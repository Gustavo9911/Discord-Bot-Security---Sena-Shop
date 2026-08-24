import discord
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timezone
import aiosqlite
import os

from database import init_db, DB_PATH
from invite_tracker import InviteTracker
from verification import VerificationSystem
from roles import ensure_roles
from config import TOKEN, LOG_CHANNEL_ID

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.invites = True

bot = commands.Bot(command_prefix="!", intents=intents)

tracker = InviteTracker(bot)
verification = VerificationSystem(bot, tracker)

# Expõe a instância para o cog de staff
bot.verification_system = verification


@bot.event
async def on_ready():
    print(f"✅ Logado como {bot.user} (ID: {bot.user.id})")
    await init_db()

    for guild in bot.guilds:
        # Cache de convites
        await tracker.cache_invites(guild)

        # Cria os cargos automaticamente se não existirem
        created, existing = await ensure_roles(guild)

        if created:
            print(f"[{guild.name}] Cargos criados: {', '.join(created)}")
        if existing:
            print(f"[{guild.name}] Cargos já existentes: {', '.join(existing)}")

    # Sincroniza os slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

    print("🚀 Bot pronto e sistema de segurança ativo.")


@bot.event
async def on_guild_join(guild: discord.Guild):
    """Quando o bot entra em um novo servidor."""
    print(f"Entrou no servidor: {guild.name} ({guild.id})")

    created, existing = await ensure_roles(guild)
    if created:
        print(f"Cargos criados em {guild.name}: {', '.join(created)}")

    await tracker.cache_invites(guild)


@bot.event
async def on_member_join(member: discord.Member):
    await verification.handle_join(member)


@bot.event
async def on_member_remove(member: discord.Member):
    """Atualiza contadores quando alguém sai."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE members SET leave_count = leave_count + 1 WHERE user_id = ?",
            (member.id,)
        )
        await db.execute(
            "UPDATE invite_uses SET left_at = ? WHERE user_id = ? AND left_at IS NULL",
            (datetime.now(timezone.utc).isoformat(), member.id)
        )
        await db.commit()

    # Log opcional
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="🚪 Membro saiu",
            description=f"{member} (`{member.id}`) saiu do servidor.",
            color=0x95a5a6,
            timestamp=datetime.now(timezone.utc)
        )
        try:
            await log_channel.send(embed=embed)
        except Exception:
            pass


@bot.event
async def on_invite_create(invite: discord.Invite):
    await tracker.cache_invites(invite.guild)


@bot.event
async def on_invite_delete(invite: discord.Invite):
    await tracker.cache_invites(invite.guild)


async def setup_hook():
    await bot.load_extension("commands.staff")


bot.setup_hook = setup_hook

if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERRO: DISCORD_TOKEN não encontrado no arquivo .env")
    else:
        bot.run(TOKEN)
