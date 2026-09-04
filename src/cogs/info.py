import math
import platform
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands
from src.bot import SlipstreamBot
from src.utils.errors import handle_command_error


def _latency_ms(bot: commands.Bot) -> str:
    latency = bot.latency
    if isinstance(latency, float) and (math.isnan(latency) or math.isinf(latency)):
        return "unknown"
    return str(round(latency * 1000))


class Info(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Info(bot))
