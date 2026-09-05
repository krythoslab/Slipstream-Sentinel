import discord
from discord import app_commands
from discord.ext import commands
from sentinel.utils import utcnow_iso, is_dangerous_role, safe_send, has_perm, hierarchy_ok
from sentinel.errors import SlipstreamError, error_response
from sentinel.embeds import success_embed, error_embed


class AutoRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def process_join(self, member: discord.Member):
        guild_id = member.guild.id
        row = await self.bot.db.fetch(
            "SELECT * FROM autorole_config WHERE guild_id = ?", (guild_id,), one=True
        )
        if not row or not row.get("enabled") or not row.get("role_id"):
            return
        role = member.guild.get_role(row["role_id"])
        if not role or is_dangerous_role(role) or role >= member.guild.me.top_role:
            return
        try:
            await member.add_roles(role, reason="Auto-role")
        except discord.Forbidden:
            pass

    @app_commands.command(name="autorole-setup", description="Configure auto-role")
    @app_commands.describe(role="Role to assign")
    async def autorole_setup(self, interaction: discord.Interaction, role: discord.Role):
        if not has_perm(interaction, "manage_roles", "administrator"):
            await error_response(interaction, "Missing permissions.")
            return
        if is_dangerous_role(role):
            await error_response(interaction, "Cannot assign dangerous roles automatically.")
            return
        if role >= interaction.guild.me.top_role:
            await error_response(interaction, "Role is too high.")
            return
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO autorole_config (guild_id, role_id) VALUES (?, ?)",
            (interaction.guild_id, role.id)
        )
        await interaction.response.send_message(embed=success_embed("Auto-role configured", f"Role: {role.name}"))

    @app_commands.command(name="autorole-enable", description="Enable auto-role")
    async def autorole_enable(self, interaction: discord.Interaction):
        if not has_perm(interaction, "manage_roles", "administrator"):
            await error_response(interaction, "Missing permissions.")
            return
        await self.bot.db.execute(
            "UPDATE autorole_config SET enabled = 1 WHERE guild_id = ?", (interaction.guild_id,)
        )
        await interaction.response.send_message(embed=success_embed("Auto-role enabled"))

    @app_commands.command(name="autorole-disable", description="Disable auto-role")
    async def autorole_disable(self, interaction: discord.Interaction):
        if not has_perm(interaction, "manage_roles", "administrator"):
            await error_response(interaction, "Missing permissions.")
            return
        await self.bot.db.execute(
            "UPDATE autorole_config SET enabled = 0 WHERE guild_id = ?", (interaction.guild_id,)
        )
        await interaction.response.send_message(embed=success_embed("Auto-role disabled"))

    @app_commands.command(name="autorole-role", description="Change the auto-role")
    @app_commands.describe(role="New role")
    async def autorole_role(self, interaction: discord.Interaction, role: discord.Role):
        if not has_perm(interaction, "manage_roles", "administrator"):
            await error_response(interaction, "Missing permissions.")
            return
        if is_dangerous_role(role):
            await error_response(interaction, "Cannot assign dangerous roles automatically.")
            return
        if role >= interaction.guild.me.top_role:
            await error_response(interaction, "Role is too high.")
            return
        await self.bot.db.execute(
            "UPDATE autorole_config SET role_id = ? WHERE guild_id = ?", (role.id, interaction.guild_id)
        )
        await interaction.response.send_message(embed=success_embed("Auto-role updated", f"Role: {role.name}"))

    @app_commands.command(name="autorole-status", description="Show auto-role status")
    async def autorole_status(self, interaction: discord.Interaction):
        row = await self.bot.db.fetch(
            "SELECT * FROM autorole_config WHERE guild_id = ?", (interaction.guild_id,), one=True
        )
        if not row:
            await interaction.response.send_message("Not configured.", ephemeral=True)
            return
        role = interaction.guild.get_role(row["role_id"]) if row.get("role_id") else None
        await interaction.response.send_message(
            f"Enabled: {bool(row.get('enabled'))} | Role: {role.name if role else 'None'}",
            ephemeral=True
        )

    @app_commands.command(name="autorole-test", description="Test auto-role on yourself")
    async def autorole_test(self, interaction: discord.Interaction):
        row = await self.bot.db.fetch(
            "SELECT * FROM autorole_config WHERE guild_id = ?", (interaction.guild_id,), one=True
        )
        if not row or not row.get("enabled") or not row.get("role_id"):
            await error_response(interaction, "Auto-role not enabled/configured.", ephemeral=True)
            return
        role = interaction.guild.get_role(row["role_id"])
        if not role or is_dangerous_role(role) or role >= interaction.guild.me.top_role:
            await error_response(interaction, "Role unavailable or too high.", ephemeral=True)
            return
        try:
            await interaction.user.add_roles(role, reason="Auto-role test")
            await interaction.response.send_message(embed=success_embed("Test passed", f"Assigned {role.name}"))
        except discord.Forbidden:
            await error_response(interaction, "Missing permissions to assign role.", ephemeral=True)
