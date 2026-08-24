import discord
from config import ROLE_PENDING, ROLE_VERIFIED, ROLE_ANALYSIS, ROLE_BLOCKED


async def ensure_roles(guild: discord.Guild):
    """
    Cria automaticamente os cargos do sistema se eles não existirem.
    Retorna: (lista_criados, lista_existentes)
    """
    roles_to_create = [
        {
            "name": ROLE_PENDING,
            "color": discord.Color.orange(),
            "hoist": True,
            "mentionable": False,
            "reason": "Sistema de Verificação - Cargo automático"
        },
        {
            "name": ROLE_VERIFIED,
            "color": discord.Color.green(),
            "hoist": True,
            "mentionable": False,
            "reason": "Sistema de Verificação - Cargo automático"
        },
        {
            "name": ROLE_ANALYSIS,
            "color": discord.Color.gold(),
            "hoist": True,
            "mentionable": False,
            "reason": "Sistema de Verificação - Cargo automático"
        },
        {
            "name": ROLE_BLOCKED,
            "color": discord.Color.dark_red(),
            "hoist": True,
            "mentionable": False,
            "reason": "Sistema de Verificação - Cargo automático"
        },
    ]

    created = []
    existing = []

    for role_data in roles_to_create:
        role = discord.utils.get(guild.roles, name=role_data["name"])

        if role is None:
            try:
                new_role = await guild.create_role(
                    name=role_data["name"],
                    color=role_data["color"],
                    hoist=role_data["hoist"],
                    mentionable=role_data["mentionable"],
                    reason=role_data["reason"]
                )
                created.append(new_role.name)
                print(f"✅ Cargo criado: {new_role.name}")
            except discord.Forbidden:
                print(f"❌ Sem permissão para criar o cargo: {role_data['name']}")
            except Exception as e:
                print(f"❌ Erro ao criar cargo {role_data['name']}: {e}")
        else:
            existing.append(role.name)

    return created, existing
