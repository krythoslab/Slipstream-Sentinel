from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from src.modules.config_storage import get_welcome_channel_id, set_welcome_channel_id
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
        embed = discord.Embed(
            title=f"Welcome to {member.guild.name}, {member.display_name}!",
            description=f"Please review the rules and introduce yourself in the introductions channel.",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Members", value=str(member.guild.member_count))
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Slipstream Motorsport")
        await channel.send(content=member.mention, embed=embed)

    @app_commands.command(name="welcome_set", description="Set the welcome channel for this server")
    async def welcome_set(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permissions.", ephemeral=True)
            return
        set_welcome_channel_id(channel.id)
        await interaction.response.send_message(f"Welcome channel set to {channel.mention}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))
