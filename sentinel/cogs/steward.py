import discord
from discord import app_commands
from discord.ext import commands
from sentinel.utils import utcnow_iso, has_perm
from sentinel.errors import error_response
from sentinel.embeds import success_embed, error_embed


class Steward(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="steward-report", description="File a steward report")
    @app_commands.describe(target="Target user", reason="Reason", evidence="Evidence")
    async def steward_report(self, interaction: discord.Interaction, target: discord.User, reason: str, evidence: str = None):
        if not target or not reason:
            await error_response(interaction, "Target and reason required.", ephemeral=True)
            return
        case_id = await self.bot.db.execute(
            "INSERT INTO steward_cases (guild_id, reporter_id, target_id, reason, evidence, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (interaction.guild_id, interaction.user.id, target.id, reason, evidence, "open", utcnow_iso(), utcnow_iso())
        )
        await interaction.response.send_message(f"Case #{case_id} opened.")

    @app_commands.command(name="steward-cases", description="List steward cases")
    async def steward_cases(self, interaction: discord.Interaction):
        rows = await self.bot.db.fetch(
            "SELECT * FROM steward_cases WHERE guild_id = ? ORDER BY id DESC LIMIT 10",
            (interaction.guild_id,)
        )
        if not rows:
            await interaction.response.send_message("No cases.")
            return
        lines = [f"#{r['id']} {r['status']} <@{r['target_id']}>: {r['reason']}" for r in rows]
        await interaction.response.send_message("\n".join(lines))

    @app_commands.command(name="steward-close", description="Close a steward case")
    @app_commands.describe(case_id="Case ID", penalty="Penalty")
    async def steward_close(self, interaction: discord.Interaction, case_id: int, penalty: str = None):
        row = await self.bot.db.fetch(
            "SELECT * FROM steward_cases WHERE id = ? AND guild_id = ?", (case_id, interaction.guild_id), one=True
        )
        if not row:
            await error_response(interaction, "Case not found.", ephemeral=True)
            return
        if not has_perm(interaction, "administrator", "moderate_members"):
            await error_response(interaction, "Missing permissions.")
            return
        await self.bot.db.execute(
            "UPDATE steward_cases SET status = 'closed', penalty = ?, closed_by = ?, updated_at = ? WHERE id = ?",
            (penalty, interaction.user.id, utcnow_iso(), case_id)
        )
        await interaction.response.send_message(f"Case #{case_id} closed.")
