import discord
from datetime import datetime, timezone
import aiosqlite

from database import DB_PATH, log_event
from risk_engine import calculate_risk
from config import (
    ROLE_PENDING, ROLE_VERIFIED, ROLE_ANALYSIS, ROLE_BLOCKED,
    LOG_CHANNEL_ID
)


class VerificationSystem:
    def __init__(self, bot, invite_tracker):
        self.bot = bot
        self.tracker = invite_tracker

    async def handle_join(self, member: discord.Member):
        if member.bot:
            return

        guild = member.guild

        # 1. Encontrar convite usado
        used_invite = await self.tracker.find_used_invite(member)
        invite_code = used_invite.code if used_invite else "desconhecido"
        inviter_id = used_invite.inviter.id if used_invite and used_invite.inviter else None

        # 2. Dados históricos
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT leave_count FROM members WHERE user_id = ?",
                (member.id,)
            )
            row = await cursor.fetchone()
            previous_joins = row[0] if row else 0

            # Contas recentes do mesmo inviter (últimas 24h)
            same_inviter = 0
            if inviter_id:
                cursor = await db.execute("""
                    SELECT COUNT(*) FROM invite_uses
                    WHERE inviter_id = ? AND joined_at > datetime('now', '-1 day')
                """, (inviter_id,))
                same_inviter = (await cursor.fetchone())[0]

        # 3. Calcular risco
        score, level, reasons = calculate_risk(
            member,
            invite_data={"temporary": used_invite.temporary if used_invite else False},
            previous_joins=previous_joins,
            same_inviter_recent=same_inviter
        )

        # 4. Roles
        pending_role = discord.utils.get(guild.roles, name=ROLE_PENDING)
        analysis_role = discord.utils.get(guild.roles, name=ROLE_ANALYSIS)

        if level == "high":
            status = "analysis"
            role_to_add = analysis_role or pending_role
        else:
            status = "pending"
            role_to_add = pending_role

        if role_to_add:
            try:
                await member.add_roles(role_to_add, reason=f"Risco {level} - score {score}")
            except discord.Forbidden:
                print(f"Sem permissão para adicionar cargo a {member}")
            except Exception as e:
                print(f"Erro ao adicionar cargo: {e}")

        # 5. Salvar no banco
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO members
                (user_id, username, account_created_at, first_join_at, last_join_at,
                 leave_count, invite_code, inviter_id, risk_score, risk_level, status)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    last_join_at = excluded.last_join_at,
                    invite_code = excluded.invite_code,
                    inviter_id = excluded.inviter_id,
                    risk_score = excluded.risk_score,
                    risk_level = excluded.risk_level,
                    status = excluded.status
            """, (
                member.id, str(member), member.created_at.isoformat(),
                now, now, invite_code, inviter_id, score, level, status
            ))

            await db.execute("""
                INSERT INTO invite_uses
                (invite_code, inviter_id, user_id, joined_at, risk_score, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (invite_code, inviter_id, member.id, now, score, status))
            await db.commit()

        # 6. Log no canal da staff
        risk_emoji = {"low": "🟢", "moderate": "🟡", "high": "🔴"}.get(level, "⚪")
        reasons_text = "\n".join(f"• {r}" for r in reasons) if reasons else "Nenhum sinal suspeito"

        embed = discord.Embed(
            title=f"{risk_emoji} Novo membro — Risco {level.upper()}",
            color=0x2ecc71 if level == "low" else (0xf1c40f if level == "moderate" else 0xe74c3c),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Membro", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Conta criada", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Convite", value=f"`{invite_code}`", inline=True)
        embed.add_field(
            name="Convidado por",
            value=f"<@{inviter_id}>" if inviter_id else "Desconhecido",
            inline=True
        )
        embed.add_field(name="Score de Risco", value=f"**{score}**", inline=True)
        embed.add_field(name="Status", value=status.upper(), inline=True)
        embed.add_field(name="Sinais detectados", value=reasons_text, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)

        log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            try:
                await log_channel.send(embed=embed)
            except Exception:
                pass

        await log_event("member_join", member.id, f"Score {score} | {level} | Invite {invite_code}")

    async def approve_member(self, member: discord.Member, moderator: discord.Member = None, auto: bool = False):
        guild = member.guild
        verified = discord.utils.get(guild.roles, name=ROLE_VERIFIED)
        pending = discord.utils.get(guild.roles, name=ROLE_PENDING)
        analysis = discord.utils.get(guild.roles, name=ROLE_ANALYSIS)

        roles_to_remove = [r for r in [pending, analysis] if r and r in member.roles]
        if roles_to_remove:
            try:
                await member.remove_roles(*roles_to_remove, reason="Verificação aprovada")
            except Exception:
                pass

        if verified:
            try:
                await member.add_roles(verified, reason="Verificação aprovada")
            except Exception:
                pass

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE members SET status = 'verified', is_valid_invite = 1 WHERE user_id = ?",
                (member.id,)
            )
            await db.execute(
                "UPDATE invite_uses SET is_valid = 1, status = 'verified' WHERE user_id = ? AND left_at IS NULL",
                (member.id,)
            )
            await db.commit()

        who = "Sistema (auto)" if auto else (moderator.mention if moderator else "Staff")
        embed = discord.Embed(
            title="✅ Membro Verificado",
            description=f"{member.mention} foi aprovado por {who}",
            color=0x2ecc71,
            timestamp=datetime.now(timezone.utc)
        )
        log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            try:
                await log_channel.send(embed=embed)
            except Exception:
                pass

        await log_event("member_approved", member.id, f"Por {who}")

    async def reject_member(self, member: discord.Member, moderator: discord.Member, reason: str = "Não passou na verificação"):
        blocked = discord.utils.get(member.guild.roles, name=ROLE_BLOCKED)
        pending = discord.utils.get(member.guild.roles, name=ROLE_PENDING)
        analysis = discord.utils.get(member.guild.roles, name=ROLE_ANALYSIS)

        roles_to_remove = [r for r in [pending, analysis] if r and r in member.roles]
        if roles_to_remove:
            try:
                await member.remove_roles(*roles_to_remove, reason=reason)
            except Exception:
                pass

        if blocked:
            try:
                await member.add_roles(blocked, reason=reason)
            except Exception:
                pass
        else:
            try:
                await member.kick(reason=reason)
            except Exception:
                pass

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE members SET status = 'blocked' WHERE user_id = ?",
                (member.id,)
            )
            await db.execute(
                "UPDATE invite_uses SET is_valid = 0, status = 'blocked' WHERE user_id = ? AND left_at IS NULL",
                (member.id,)
            )
            await db.commit()

        embed = discord.Embed(
            title="🚫 Membro Rejeitado / Bloqueado",
            description=f"{member.mention} foi rejeitado por {moderator.mention}\n**Motivo:** {reason}",
            color=0xe74c3c,
            timestamp=datetime.now(timezone.utc)
        )
        log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            try:
                await log_channel.send(embed=embed)
            except Exception:
                pass

        await log_event("member_rejected", member.id, reason)
