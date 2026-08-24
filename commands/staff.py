import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from datetime import datetime, timezone

from database import DB_PATH
from config import STAFF_ROLE_ID, ROLE_VERIFIED, ROLE_PENDING, ROLE_ANALYSIS, ROLE_BLOCKED


class StaffCommands(commands.Cog):
    def __init__(self, bot, verification_system):
        self.bot = bot
        self.verification = verification_system

    def is_staff():
        async def predicate(interaction: discord.Interaction):
            if interaction.user.guild_permissions.administrator:
                return True
            if STAFF_ROLE_ID and any(r.id == STAFF_ROLE_ID for r in interaction.user.roles):
                return True
            return False
        return app_commands.check(predicate)

    @app_commands.command(name="verificar", description="Aprova, rejeita ou coloca um membro em análise")
    @app_commands.describe(
        membro="O membro a ser gerenciado",
        acao="aprovar | rejeitar | analisar",
        motivo="Motivo da ação (opcional)"
    )
    @is_staff()
    async def verificar(
        self,
        interaction: discord.Interaction,
        membro: discord.Member,
        acao: str,
        motivo: str = "Sem motivo informado"
    ):
        acao = acao.lower().strip()

        if acao in ("aprovar", "approve", "sim", "yes"):
            await self.verification.approve_member(membro, interaction.user)
            await interaction.response.send_message(
                f"✅ {membro.mention} foi **aprovado** e recebeu o cargo de verificado.",
                ephemeral=True
            )

        elif acao in ("rejeitar", "reject", "bloquear", "ban", "kick"):
            await self.verification.reject_member(membro, interaction.user, motivo)
            await interaction.response.send_message(
                f"🚫 {membro.mention} foi **rejeitado/bloqueado**.\nMotivo: {motivo}",
                ephemeral=True
            )

        elif acao in ("analisar", "analysis", "revisar"):
            analysis_role = discord.utils.get(interaction.guild.roles, name=ROLE_ANALYSIS)
            pending_role = discord.utils.get(interaction.guild.roles, name=ROLE_PENDING)

            if analysis_role:
                roles_to_remove = [r for r in [pending_role] if r and r in membro.roles]
                if roles_to_remove:
                    await membro.remove_roles(*roles_to_remove)
                await membro.add_roles(analysis_role, reason="Colocado em análise pela staff")

            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE members SET status = 'analysis' WHERE user_id = ?",
                    (membro.id,)
                )
                await db.commit()

            await interaction.response.send_message(
                f"⚠️ {membro.mention} foi colocado em **análise**.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Ação inválida. Use: `aprovar`, `rejeitar` ou `analisar`.",
                ephemeral=True
            )

    @app_commands.command(name="info", description="Mostra informações de segurança de um membro")
    @is_staff()
    async def info(self, interaction: discord.Interaction, membro: discord.Member):
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT * FROM members WHERE user_id = ?",
                (membro.id,)
            )
            row = await cursor.fetchone()

        if not row:
            return await interaction.response.send_message(
                "Membro ainda não registrado no sistema de segurança.",
                ephemeral=True
            )

        # Índices: 0=user_id, 1=username, 2=account_created, 3=first_join,
        # 4=last_join, 5=leave_count, 6=invite_code, 7=inviter_id,
        # 8=risk_score, 9=risk_level, 10=status, 11=is_valid, 12=notes

        risk_emoji = {"low": "🟢", "moderate": "🟡", "high": "🔴"}.get(row[9], "⚪")
        status_emoji = {
            "pending": "🔍",
            "verified": "✅",
            "analysis": "⚠️",
            "blocked": "🚫"
        }.get(row[10], "❓")

        embed = discord.Embed(
            title=f"📋 Info de Segurança — {membro}",
            color=0x3498db,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=membro.display_avatar.url)

        embed.add_field(name="Status", value=f"{status_emoji} {row[10].upper()}", inline=True)
        embed.add_field(name="Risco", value=f"{risk_emoji} {row[8]} ({row[9]})", inline=True)
        embed.add_field(name="Convite Válido", value="Sim" if row[11] else "Não", inline=True)

        embed.add_field(name="Convite usado", value=f"`{row[6] or 'desconhecido'}`", inline=True)
        embed.add_field(
            name="Convidado por",
            value=f"<@{row[7]}>" if row[7] else "Desconhecido",
            inline=True
        )
        embed.add_field(name="Saídas", value=str(row[5] or 0), inline=True)

        try:
            created_ts = int(datetime.fromisoformat(row[2]).timestamp())
            embed.add_field(name="Conta criada", value=f"<t:{created_ts}:R>", inline=True)
        except Exception:
            embed.add_field(name="Conta criada", value=row[2] or "?", inline=True)

        try:
            first_join_ts = int(datetime.fromisoformat(row[3]).timestamp())
            embed.add_field(name="Primeira entrada", value=f"<t:{first_join_ts}:R>", inline=True)
        except Exception:
            pass

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ranking", description="Ranking de convites válidos")
    @is_staff()
    async def ranking(self, interaction: discord.Interaction):
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                SELECT inviter_id,
                       COUNT(*) as total,
                       SUM(CASE WHEN is_valid = 1 THEN 1 ELSE 0 END) as validos,
                       SUM(CASE WHEN left_at IS NOT NULL THEN 1 ELSE 0 END) as saidas,
                       SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) as bloqueados
                FROM invite_uses
                WHERE inviter_id IS NOT NULL
                GROUP BY inviter_id
                ORDER BY validos DESC
                LIMIT 15
            """)
            rows = await cursor.fetchall()

        if not rows:
            return await interaction.response.send_message(
                "Ainda não há dados de convites.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="🏆 Ranking de Convites Válidos",
            description="Conta apenas membros que passaram na verificação e não foram bloqueados.",
            color=0xf1c40f,
            timestamp=datetime.now(timezone.utc)
        )

        for i, (inviter, total, validos, saidas, bloqueados) in enumerate(rows, 1):
            embed.add_field(
                name=f"{i}. <@{inviter}>",
                value=(
                    f"✅ Válidos: **{validos or 0}**\n"
                    f"📥 Total: {total or 0}\n"
                    f"🚪 Saíram: {saidas or 0}\n"
                    f"🚫 Bloqueados: {bloqueados or 0}"
                ),
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="meus-convites", description="Mostra quantos convites válidos você tem")
    async def meus_convites(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN is_valid = 1 THEN 1 ELSE 0 END) as validos,
                    SUM(CASE WHEN left_at IS NOT NULL THEN 1 ELSE 0 END) as saidas,
                    SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) as bloqueados
                FROM invite_uses
                WHERE inviter_id = ?
            """, (user_id,))
            row = await cursor.fetchone()

        total, validos, saidas, bloqueados = row or (0, 0, 0, 0)

        embed = discord.Embed(
            title="🎟️ Seus Convites",
            color=0x3498db,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="✅ Válidos", value=str(validos or 0), inline=True)
        embed.add_field(name="📥 Total", value=str(total or 0), inline=True)
        embed.add_field(name="🚪 Saíram", value=str(saidas or 0), inline=True)
        embed.add_field(name="🚫 Bloqueados / Fakes", value=str(bloqueados or 0), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    # A instância de verification será injetada no bot.py
    verification = getattr(bot, "verification_system", None)
    await bot.add_cog(StaffCommands(bot, verification))
