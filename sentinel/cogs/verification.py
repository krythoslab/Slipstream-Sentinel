import discord
from discord import app_commands
from discord.ext import commands
from sentinel.utils import utcnow_iso, has_perm
from sentinel.errors import error_response
from sentinel.embeds import success_embed, error_embed


class Verification(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def process_join(self, member: discord.Member):
        guild_id = member.guild.id
        row = await self.bot.db.fetch(
            "SELECT * FROM verification_config WHERE guild_id = ?", (guild_id,), one=True
        )
        if not row or not row.get("enabled") or not row.get("role_id") or not row.get("channel_id"):
            return
        role = member.guild.get_role(row["role_id"])
        if not role or is_dangerous_role(role) or role >= member.guild.me.top_role:
            return
        account_age = (utcnow() - member.created_at).days
        if account_age >= row.get("min_account_age_days", 7):
            try:
                await member.add_roles(role, reason="Verification passed")
            except discord.Forbidden:
                pass

    @app_commands.command(name="verify-setup", description="Configure verification")
    @app_commands.describe(channel="Verification channel", role="Verified role", min_age="Minimum account age (days)")
    async def verify_setup(self, interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role, min_age: int = 7):
        if not has_perm(interaction, "administrator", "manage_guild"):
            await error_response(interaction, "Missing permissions.")
            return
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO verification_config (guild_id, channel_id, role_id, min_account_age_days) VALUES (?, ?, ?, ?)",
            (interaction.guild_id, channel.id, role.id, min_age)
        )
        await interaction.response.send_message(embed=success_embed("Verification configured", f"{channel.mention} -> {role.name}"))

    @app_commands.command(name="verify-enable", description="Enable verification")
    async def verify_enable(self, interaction: discord.Interaction):
        if not has_perm(interaction, "administrator", "manage_guild"):
            await error_response(interaction, "Missing permissions.")
            return
        await self.bot.db.execute(
            "UPDATE verification_config SET enabled = 1 WHERE guild_id = ?", (interaction.guild_id,)
        )
        await interaction.response.send_message(embed=success_embed("Verification enabled"))

    @app_commands.command(name="verify-disable", description="Disable verification")
    async def verify_disable(self, interaction: discord.Interaction):
        if not has_perm(interaction, "administrator", "manage_guild"):
            await error_response(interaction, "Missing permissions.")
            return
        await self.bot.db.execute(
            "UPDATE verification_config SET enabled = 0 WHERE guild_id = ?", (interaction.guild_id,)
        )
        await interaction.response.send_message(embed=success_embed("Verification disabled"))

    @app_commands.command(name="verify-status", description="Show verification status")
    async def verify_status(self, interaction: discord.Interaction):
        row = await self.bot.db.fetch(
            "SELECT * FROM verification_config WHERE guild_id = ?", (interaction.guild_id,), one=True
        )
        if not row:
            await interaction.response.send_message("Not configured.", ephemeral=True)
            return
        ch = interaction.guild.get_channel(row["channel_id"]) if row.get("channel_id") else None
        role = interaction.guild.get_role(row["role_id"]) if row.get("role_id") else None
        await interaction.response.send_message(
            f"Enabled: {bool(row.get('enabled'))} | Channel: {ch.name if ch else 'None'} | Role: {role.name if role else 'None'} | Min age: {row.get('min_account_age_days', 7)} days",
            ephemeral=True
        )

    @app_commands.command(name="verify-reset", description="Reset verification configuration")
    async def verify_reset(self, interaction: discord.Interaction):
        if not has_perm(interaction, "administrator", "manage_guild"):
            await error_response(interaction, "Missing permissions.")
            return
        await self.bot.db.execute(
            "DELETE FROM verification_config WHERE guild_id = ?", (interaction.guild_id,)
        )
        await interaction.response.send_message(embed=success_embed("Verification reset"))
