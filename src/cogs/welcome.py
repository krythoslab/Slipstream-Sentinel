from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from src.modules.config_storage import (
    get_welcome_channel_id,
    set_welcome_channel_id,
    get_leave_channel_id,
    set_leave_channel_id,
    get_welcome_message,
    set_welcome_message,
    get_leave_message,
    set_leave_message,
)
from src.utils.errors import handle_command_error


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        channel_id = get_welcome_channel_id()
        if not channel_id:
            return
        channel = self.bot.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        message_template = get_welcome_message()
        content = message_template.replace("{server}", member.guild.name).replace("{user}", member.display_name)
        embed = discord.Embed(
            title=f"Welcome to {member.guild.name}, {member.display_name}!",
            description=content,
            color=discord.Color.blue(),
        )
        embed.add_field(name="Members", value=str(member.guild.member_count))
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Slipstream Motorsport")
        await channel.send(content=member.mention, embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        channel_id = get_leave_channel_id()
        if not channel_id:
            return
        channel = self.bot.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        message_template = get_leave_message()
        content = message_template.replace("{server}", member.guild.name).replace("{user}", member.display_name)
        embed = discord.Embed(
            title=f"Goodbye, {member.display_name}!",
            description=content,
            color=discord.Color.red(),
        )
        embed.set_footer(text="Slipstream Motorsport")
        await channel.send(embed=embed)

    @app_commands.command(name="welcome_set", description="Set the welcome channel for this server")
    async def welcome_set(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permissions.", ephemeral=True)
            return
        set_welcome_channel_id(channel.id)
        await interaction.response.send_message(f"Welcome channel set to {channel.mention}")

    @app_commands.command(name="leave_set", description="Set the leave channel for this server")
    async def leave_set(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permissions.", ephemeral=True)
            return
        set_leave_channel_id(channel.id)
        await interaction.response.send_message(f"Leave channel set to {channel.mention}")

    @app_commands.command(name="welcome_message_set", description="Set the welcome message template")
    async def welcome_message_set(self, interaction: discord.Interaction, message: str) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permissions.", ephemeral=True)
            return
        set_welcome_message(message)
        await interaction.response.send_message("Welcome message updated. Use {server} and {user} as placeholders.")

    @app_commands.command(name="leave_message_set", description="Set the leave message template")
    async def leave_message_set(self, interaction: discord.Interaction, message: str) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permissions.", ephemeral=True)
            return
        set_leave_message(message)
        await interaction.response.send_message("Leave message updated. Use {server} and {user} as placeholders.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))