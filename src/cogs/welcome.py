from typing import Optional
import os
import discord
from discord import app_commands
from discord.ext import commands
from src.config import WELCOME_CHANNEL_ID
from src.utils.errors import handle_command_error


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
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
        import os
        os.environ["WELCOME_CHANNEL_ID"] = str(channel.id)
        global WELCOME_CHANNEL_ID
        WELCOME_CHANNEL_ID = channel.id
        await interaction.response.send_message(f"Welcome channel set to {channel.mention}")
