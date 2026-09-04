from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from src.modules import config_storage
from src.utils.errors import handle_command_error


class Config(commands.GroupCog, name="config"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    @app_commands.command(name="welcome_channel", description="Set the welcome channel")
    async def config_welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        config_storage.set_welcome_channel_id(channel.id)
        await interaction.response.send_message(f"Welcome channel set to {channel.mention}")

    @app_commands.command(name="leave_channel", description="Set the leave channel")
    async def config_leave_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        config_storage.set_leave_channel_id(channel.id)
        await interaction.response.send_message(f"Leave channel set to {channel.mention}")

    @app_commands.command(name="modlog_channel", description="Set the modlog channel")
    async def config_modlog_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        config_storage.set_modlog_channel_id(channel.id)
        await interaction.response.send_message(f"Modlog channel set to {channel.mention}")

    @app_commands.command(name="announcement_channel", description="Set the announcement channel")
    async def config_announcement_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        config_storage.set_announcement_channel_id(channel.id)
        await interaction.response.send_message(f"Announcement channel set to {channel.mention}")

    @app_commands.command(name="automod_alert_channel", description="Set the AutoMod alert channel")
    async def config_automod_alert_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        config_storage.set_automod_alert_channel_id(channel.id)
        await interaction.response.send_message(f"AutoMod alert channel set to {channel.mention}")

    @app_commands.command(name="welcome_message", description="Set the welcome message template")
    async def config_welcome_message(self, interaction: discord.Interaction, message: str) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        config_storage.set_welcome_message(message)
        await interaction.response.send_message("Welcome message updated.")

    @app_commands.command(name="leave_message", description="Set the leave message template")
    async def config_leave_message(self, interaction: discord.Interaction, message: str) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        config_storage.set_leave_message(message)
        await interaction.response.send_message("Leave message updated.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Config(bot))
