import discord


class InviteTracker:
    def __init__(self, bot):
        self.bot = bot
        self.invite_cache = {}  # guild_id -> {code: uses}

    async def cache_invites(self, guild: discord.Guild):
        try:
            invites = await guild.invites()
            self.invite_cache[guild.id] = {inv.code: inv.uses for inv in invites}
        except discord.Forbidden:
            print(f"[InviteTracker] Sem permissão para ver convites em {guild.name}")
        except Exception as e:
            print(f"[InviteTracker] Erro ao cachear convites: {e}")

    async def find_used_invite(self, member: discord.Member):
        """Compara o cache anterior com os convites atuais para descobrir qual foi usado."""
        guild = member.guild
        try:
            current = await guild.invites()
        except discord.Forbidden:
            return None
        except Exception:
            return None

        cached = self.invite_cache.get(guild.id, {})
        used = None

        for inv in current:
            before = cached.get(inv.code, 0)
            if inv.uses > before:
                used = inv
                break

        # Atualiza o cache
        self.invite_cache[guild.id] = {inv.code: inv.uses for inv in current}
        return used
