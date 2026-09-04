from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from src.utils.errors import handle_command_error


class League(commands.GroupCog, name="league"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    @app_commands.command(name="register", description="Register as a driver")
    @app_commands.describe(number="Your driver number")
    async def register(self, interaction: discord.Interaction, number: int) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        import sqlite3
        from src.config import MODLOG_DB_FILE
        try:
            with sqlite3.connect(MODLOG_DB_FILE) as conn:
                conn.execute(
                    "INSERT INTO league_drivers (guild_id, user_id, number, created_at) VALUES (?, ?, ?, ?)",
                    (interaction.guild_id, interaction.user.id, number, discord.utils.utcnow().isoformat()),
                )
            await interaction.response.send_message(f"Registered as driver #{number}")
        except Exception:
            await interaction.response.send_message("Registration failed. You may already be registered.", ephemeral=True)

    @app_commands.command(name="team", description="Set your team")
    @app_commands.describe(team_name="Your team name")
    async def team(self, interaction: discord.Interaction, team_name: str) -> None:
        import sqlite3
        from src.config import MODLOG_DB_FILE
        with sqlite3.connect(MODLOG_DB_FILE) as conn:
            conn.execute(
                "UPDATE league_drivers SET team_name = ? WHERE guild_id = ? AND user_id = ?",
                (team_name, interaction.guild_id, interaction.user.id),
            )
        await interaction.response.send_message(f"Team set to {team_name}")

    @app_commands.command(name="standings", description="Show driver standings")
    async def standings(self, interaction: discord.Interaction) -> None:
        import sqlite3
        from src.config import MODLOG_DB_FILE
        with sqlite3.connect(MODLOG_DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT driver_id, SUM(points) as total FROM league_results WHERE guild_id = ? GROUP BY driver_id ORDER BY total DESC LIMIT 20",
                (interaction.guild_id,),
            ).fetchall()
        if not rows:
            await interaction.response.send_message("No standings available.", ephemeral=True)
            return
        lines = [f"#{i+1} <@{row['driver_id']}> - {row['total']} pts" for i, row in enumerate(rows)]
        await interaction.response.send_message("\n".join(lines))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(League(bot))
