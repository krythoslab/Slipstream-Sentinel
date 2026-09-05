import discord
from discord import app_commands
from sentinel.utils import has_perm, hierarchy_ok, is_dangerous_role


class SlipstreamError(Exception):
    pass


async def error_response(interaction: discord.Interaction, message: str, ephemeral: bool = True):
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(message, ephemeral=ephemeral)
    except Exception:
        pass


def require_perms(*perms: str):
    async def predicate(interaction: discord.Interaction):
        if not has_perm(interaction, *perms):
            raise SlipstreamError("Missing permissions.")
        return True
    return app_commands.check(predicate)


def require_hierarchy(target: discord.Member):
    async def predicate(interaction: discord.Interaction):
        if not hierarchy_ok(interaction.user, target):
            raise SlipstreamError("Role hierarchy too low.")
        return True
    return app_commands.check(predicate)


def bot_can_manage_role(interaction: discord.Interaction, role: discord.Role) -> bool:
    return role < interaction.guild.me.top_role and not is_dangerous_role(role)
