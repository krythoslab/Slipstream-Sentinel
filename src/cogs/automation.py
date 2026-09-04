from datetime import datetime, timezone
import discord
from discord import app_commands
from discord.ext import commands, tasks
from src.modules import config_storage
from src.utils.errors import handle_command_error


class Automation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.reminder_loop.start()

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    def cog_unload(self) -> None:
        self.reminder_loop.cancel()

    @tasks.loop(minutes=30)
    async def reminder_loop(self) -> None:
        now = datetime.now(timezone.utc)
        self.bot.logger.info("Automation loop running at %s", now.isoformat())

    @reminder_loop.before_loop
    async def before_reminder_loop(self) -> None:
        await self.bot.wait_until_ready()

    @app_commands.command(name="remind", description="Set a reminder")
    @app_commands.describe(seconds="Seconds until reminder", message="Reminder message")
    async def remind(self, interaction: discord.Interaction, seconds: int, message: str) -> None:
        if seconds < 1 or seconds > 86400:
            await interaction.response.send_message("Reminder must be between 1 and 86400 seconds.", ephemeral=True)
            return
        await interaction.response.send_message(f"Reminder set for {seconds} seconds.")
        await discord.utils.sleep_until(datetime.now(timezone.utc))
        try:
            await interaction.user.send(f"Reminder: {message}")
        except Exception:
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Automation(bot))
