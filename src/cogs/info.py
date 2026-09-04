import math
import platform
from datetime import datetime, timezone
import logging

import discord
from discord import app_commands
from discord.ext import commands
from src.bot import SlipstreamBot
from src.utils.errors import handle_command_error

logger = logging.getLogger("slipstream.info")


def _latency_ms(bot: commands.Bot) -> str:
    latency = bot.latency
    if isinstance(latency, float) and (math.isnan(latency) or math.isinf(latency)):
        return "unknown"
    return str(round(latency * 1000))


class Info(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        logger.exception("Error in Info cog command: %s", error)
        await handle_command_error(interaction, error)

    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"Pong! {_latency_ms(self.bot)} ms")

    @app_commands.command(name="about", description="Bot information")
    async def about(self, interaction: discord.Interaction) -> None:
        bot: SlipstreamBot = self.bot
        uptime = datetime.now(timezone.utc) - bot.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        embed = discord.Embed(
            title="Slipstream Sentinel",
            description="Production-ready Discord bot for Slipstream Motorsport.",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Latency", value=f"{_latency_ms(self.bot)} ms")
        embed.add_field(name="Uptime", value=f"{hours}h {minutes}m")
        embed.add_field(name="Python", value=platform.python_version())
        embed.add_field(name="Discord.py", value=discord.__version__)
        embed.set_footer(text="Slipstream Motorsport")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="help", description="Show available commands")
    async def help(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="Slipstream Sentinel - Command Help",
            description="Use slash commands to interact with the bot.",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="General", value="/ping, /about, /help, /status", inline=False)
        embed.add_field(name="Moderation (/mod)", value="/mod warn, /mod unwarn, /mod warnings, /mod timeout, /mod untimeout, /mod kick, /mod ban, /mod unban, /mod purge, /mod lock, /mod unlock, /mod slowmode, /mod history", inline=False)
        embed.add_field(name="AutoMod", value="/automod_add, /automod_remove, /automod_list, /automod exempt, /automod config", inline=False)
        embed.add_field(name="Welcome", value="/welcome_set, /leave_set, /welcome_message_set, /leave_message_set", inline=False)
        embed.add_field(name="Config", value="/config", inline=False)
        embed.add_field(name="Announcements", value="/announce", inline=False)
        embed.add_field(name="Polls", value="/poll", inline=False)
        embed.add_field(name="Roles", value="/role", inline=False)
        embed.add_field(name="Info", value="/serverinfo, /userinfo", inline=False)
        embed.add_field(name="Admin", value="/admin reload", inline=False)
        embed.set_footer(text="Slipstream Motorsport")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="status", description="Set the bot's activity status")
    @app_commands.describe(activity="The activity to set (playing, watching, listening, streaming)", text="The status text")
    async def status(self, interaction: discord.Interaction, activity: str, text: str) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permissions.", ephemeral=True)
            return
        activity_type_map = {
            "playing": discord.ActivityType.playing,
            "watching": discord.ActivityType.watching,
            "listening": discord.ActivityType.listening,
            "streaming": discord.ActivityType.streaming,
        }
        activity_type = activity_type_map.get(activity.lower())
        if activity_type is None:
            await interaction.response.send_message("Invalid activity type. Use: playing, watching, listening, streaming", ephemeral=True)
            return
        await self.bot.change_presence(activity=discord.Activity(type=activity_type, name=text))
        await interaction.response.send_message(f"Status set to {activity} {text}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Info(bot))
