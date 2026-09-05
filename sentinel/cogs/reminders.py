import discord
from discord import app_commands
from discord.ext import commands
from sentinel.utils import utcnow_iso, has_perm, parse_duration
from sentinel.errors import error_response
from sentinel.embeds import success_embed, error_embed


class Reminders(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="remind", description="Set a reminder")
    @app_commands.describe(what="What to remind you about", when="Duration e.g. 1h, 30m, 1d")
    async def remind(self, interaction: discord.Interaction, what: str, when: str):
        try:
            seconds = parse_duration(when)
        except ValueError:
            await error_response(interaction, "Invalid duration. Use 1h, 30m, or 1d.", ephemeral=True)
            return
        from datetime import datetime, timezone, timedelta
        due_at = (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()
        await self.bot.db.execute(
            "INSERT INTO reminders (user_id, guild_id, channel_id, content, due_at) VALUES (?, ?, ?, ?, ?)",
            (interaction.user.id, interaction.guild_id, interaction.channel_id, what, due_at)
        )
        await interaction.response.send_message(f"Reminder set for {when}: {what}")
