from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from src.modules import config_storage
from src.utils.errors import handle_command_error


class Announcements(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    @app_commands.command(name="announce", description="Send an announcement to the configured channel")
    @app_commands.describe(title="Announcement title", message="Announcement message")
    async def announce(self, interaction: discord.Interaction, title: str, message: str) -> None:
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        channel_id = config_storage.get_announcement_channel_id()
        if not channel_id:
            await interaction.response.send_message("Announcement channel not configured. Use /config announcement_channel.", ephemeral=True)
            return
        channel = self.bot.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Announcement channel not found.", ephemeral=True)
            return
        embed = discord.Embed(
            title=title,
            description=message,
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"Announced by {interaction.user}")
        await channel.send(embed=embed)
        await interaction.response.send_message(f"Announcement sent to {channel.mention}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Announcements(bot))
