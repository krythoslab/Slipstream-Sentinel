import discord
from discord import app_commands
from discord.ext import commands
from src.utils.errors import handle_command_error
from src.utils.helpers import ensure_mod_permissions


class Admin(commands.GroupCog, name="admin"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    @app_commands.command(name="reload", description="Reload a cog")
    async def reload(self, interaction: discord.Interaction, cog: str) -> None:
        if not await ensure_mod_permissions(interaction):
            return
        try:
            await self.bot.reload_extension(f"src.cogs.{cog}")
            await interaction.response.send_message(f"Reloaded cog: {cog}")
        except Exception as exc:
            await interaction.response.send_message(f"Failed to reload: {exc}", ephemeral=True)
