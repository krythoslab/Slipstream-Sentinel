import discord
from discord import app_commands
from discord.ext import commands
from sentinel.utils import utcnow_iso


class Core(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! {round(self.bot.latency * 1000)}ms")

    @app_commands.command(name="status", description="Bot status overview")
    async def status(self, interaction: discord.Interaction):
        uptime = discord.utils.format_dt(self.bot._start, style="R")
        await interaction.response.send_message(
            f"Servers: {len(self.bot.guilds)} | Uptime: {uptime} | Latency: {round(self.bot.latency*1000)}ms"
        )

    @app_commands.command(name="about", description="About Slipstream Sentinel")
    async def about(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Slipstream Sentinel",
            description="Production-quality multi-server Discord moderation & league bot.",
            color=0x0099ff,
            timestamp=discord.utils.parse_time(utcnow_iso())
        )
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Prefix", value="Slash commands only", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="help", description="Show help menu")
    async def help(self, interaction: discord.Interaction):
        categories = {
            "Core": ["/ping", "/status", "/about", "/help"],
            "Auto Role": ["/autorole-setup", "/autorole-enable", "/autorole-disable", "/autorole-role", "/autorole-status", "/autorole-test"],
            "Welcome": ["/welcome-setup", "/welcome-enable", "/welcome-disable", "/welcome-test"],
            "Leave": ["/leave-setup", "/leave-enable", "/leave-disable", "/leave-test"],
            "Moderation": ["/warn", "/warnings", "/unwarn", "/timeout", "/untimeout", "/kick", "/ban", "/unban", "/softban", "/purge", "/lock", "/unlock", "/slowmode", "/nick", "/history", "/cases"],
            "AutoMod": ["/automod-status", "/automod-whitelist", "/automod-blacklist", "/automod-thresholds"],
            "Verification": ["/verify-setup", "/verify-enable", "/verify-disable", "/verify-status", "/verify-reset"],
            "Server": ["/announce", "/role-give", "/role-remove", "/serverinfo", "/userinfo", "/poll", "/config"],
            "League": ["/league-register", "/league-team", "/league-standings", "/league-season"],
            "Race Control": ["/steward-report", "/steward-cases", "/steward-close"],
            "Reminders": ["/remind"],
        }
        lines = []
        for cat, cmds in categories.items():
            lines.append(f"**{cat}:** " + ", ".join(cmds))
        embed = discord.Embed(title="Help", description="\n".join(lines), color=0x0099ff)
        await interaction.response.send_message(embed=embed, ephemeral=True)
