from datetime import datetime, timedelta, timezone
import sqlite3

import discord
from discord import app_commands
from discord.ext import commands, tasks
from src.config import MODLOG_DB_FILE
from src.utils.errors import handle_command_error


class Automation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.reminder_loop.start()

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    def cog_unload(self) -> None:
        self.reminder_loop.cancel()

    @tasks.loop(minutes=1)
    async def reminder_loop(self) -> None:
        try:
            with sqlite3.connect(MODLOG_DB_FILE) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT id, user_id, channel_id, message FROM reminders WHERE due_at <= ? ORDER BY due_at ASC LIMIT 50",
                    (datetime.now(timezone.utc).isoformat(),),
                ).fetchall()
                if not rows:
                    return
                for row in rows:
                    try:
                        user = self.bot.get_user(row["user_id"])
                        if user is None:
                            try:
                                user = await self.bot.fetch_user(row["user_id"])
                            except Exception:
                                user = None
                        if user is not None:
                            await user.send(f"Reminder: {row['message']}")
                    except Exception:
                        pass
                conn.execute(
                    "DELETE FROM reminders WHERE id IN (%s)"
                    % ",".join(str(row["id"]) for row in rows)
                )
        except Exception as exc:
            self.bot.logger.error("Reminder loop error: %s", exc)

    @reminder_loop.before_loop
    async def before_reminder_loop(self) -> None:
        await self.bot.wait_until_ready()

    @app_commands.command(name="remind", description="Set a reminder")
    @app_commands.describe(seconds="Seconds until reminder (1-86400)", message="Reminder message")
    async def remind(self, interaction: discord.Interaction, seconds: int, message: str) -> None:
        if seconds < 1 or seconds > 86400:
            await interaction.response.send_message("Reminder must be between 1 and 86400 seconds.", ephemeral=True)
            return
        due_at = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        try:
            with sqlite3.connect(MODLOG_DB_FILE) as conn:
                conn.execute(
                    "INSERT INTO reminders (user_id, channel_id, message, due_at, created_at) VALUES (?, ?, ?, ?, ?)",
                    (interaction.user.id, interaction.channel_id, message, due_at.isoformat(), datetime.now(timezone.utc).isoformat()),
                )
        except Exception as exc:
            await interaction.response.send_message(f"Failed to set reminder: {exc}", ephemeral=True)
            return
        await interaction.response.send_message(f"Reminder set for {seconds} seconds.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Automation(bot))
