from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from src.utils.errors import handle_command_error


class RaceControl(commands.GroupCog, name="steward"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    @app_commands.command(name="report", description="File a steward incident report")
    @app_commands.describe(driver="The driver involved", description="Incident description", evidence="Evidence link (optional)")
    async def report(self, interaction: discord.Interaction, driver: discord.Member, description: str, evidence: Optional[str] = None) -> None:
        import sqlite3
        from src.config import MODLOG_DB_FILE
        with sqlite3.connect(MODLOG_DB_FILE) as conn:
            conn.execute(
                "INSERT INTO race_control_cases (guild_id, incident_number, driver_id, reporter_id, description, evidence, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    interaction.guild_id,
                    f"INC-{discord.utils.utcnow().timestamp():.0f}",
                    driver.id,
                    interaction.user.id,
                    description,
                    evidence or "",
                    "open",
                    discord.utils.utcnow().isoformat(),
                    discord.utils.utcnow().isoformat(),
                ),
            )
        await interaction.response.send_message(f"Incident report filed against {driver.mention}")

    @app_commands.command(name="cases", description="List open steward cases")
    async def cases(self, interaction: discord.Interaction) -> None:
        import sqlite3
        from src.config import MODLOG_DB_FILE
        with sqlite3.connect(MODLOG_DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT incident_number, driver_id, description, status FROM race_control_cases WHERE guild_id = ? AND status = 'open' ORDER BY created_at DESC",
                (interaction.guild_id,),
            ).fetchall()
        if not rows:
            await interaction.response.send_message("No open cases.", ephemeral=True)
            return
        lines = [f"{row['incident_number']} - <@{row['driver_id']}>: {row['description'][:50]}" for row in rows]
        await interaction.response.send_message("\n".join(lines))

    @app_commands.command(name="close", description="Close a steward case")
    @app_commands.describe(incident_number="The incident number", penalty="Penalty (optional)", reason="Dismissal reason (if no penalty)")
    async def close(self, interaction: discord.Interaction, incident_number: str, penalty: Optional[str] = None, reason: Optional[str] = None) -> None:
        import sqlite3
        from src.config import MODLOG_DB_FILE
        with sqlite3.connect(MODLOG_DB_FILE) as conn:
            if penalty:
                conn.execute(
                    "UPDATE race_control_cases SET status = 'penalized', penalty = ?, updated_at = ? WHERE incident_number = ? AND guild_id = ?",
                    (penalty, discord.utils.utcnow().isoformat(), incident_number, interaction.guild_id),
                )
            else:
                conn.execute(
                    "UPDATE race_control_cases SET status = 'dismissed', dismissed_reason = ?, updated_at = ? WHERE incident_number = ? AND guild_id = ?",
                    (reason or "No penalty", discord.utils.utcnow().isoformat(), incident_number, interaction.guild_id),
                )
        await interaction.response.send_message(f"Case {incident_number} closed.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RaceControl(bot))
