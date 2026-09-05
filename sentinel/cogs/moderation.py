import discord
from discord import app_commands
from discord.ext import commands
from sentinel.utils import utcnow_iso, has_perm, hierarchy_ok, safe_send, is_dangerous_role
from sentinel.errors import error_response
from sentinel.embeds import mod_case_embed, success_embed, error_embed
from sentinel.database import Database


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def log_action(self, guild_id: int, action: str, target_id: int, moderator_id: int, reason: str = None, duration_seconds: int = None, channel_id: int = None, message_id: int = None):
        await self.bot.db.execute(
            "INSERT INTO moderation_actions (guild_id, action, target_id, moderator_id, reason, duration_seconds, channel_id, message_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (guild_id, action, target_id, moderator_id, reason, duration_seconds, channel_id, message_id, utcnow_iso())
        )

    @app_commands.command(name="warn", description="Warn a user")
    @app_commands.describe(user="User", reason="Reason")
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided."):
        if not has_perm(interaction, "moderate_members", "kick_members", "ban_members", "administrator"):
            await error_response(interaction, "Missing permissions.")
            return
        if not hierarchy_ok(interaction.user, user):
            await error_response(interaction, "Role hierarchy too low.")
            return
        await self.bot.db.execute(
            "INSERT INTO warnings (user_id, guild_id, moderator_id, reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (user.id, interaction.guild_id, interaction.user.id, reason, utcnow_iso())
        )
        await self.log_action(interaction.guild_id, "warn", user.id, interaction.user.id, reason)
        await interaction.response.send_message(f"Warned {user.mention}: {reason}")

    @app_commands.command(name="warnings", description="List warnings for a user")
    @app_commands.describe(user="User")
    async def warnings(self, interaction: discord.Interaction, user: discord.Member):
        rows = await self.bot.db.fetch(
            "SELECT * FROM warnings WHERE user_id = ? AND guild_id = ?", (user.id, interaction.guild_id)
        )
        if not rows:
            await interaction.response.send_message("No warnings found.")
            return
        lines = [f"#{r['id']} by <@{r['moderator_id']}>: {r['reason']} ({r['created_at'][:10]})" for r in rows[:10]]
        await interaction.response.send_message("\n".join(lines))

    @app_commands.command(name="unwarn", description="Remove a warning")
    @app_commands.describe(warning_id="Warning ID")
    async def unwarn(self, interaction: discord.Interaction, warning_id: int):
        row = await self.bot.db.fetch("SELECT * FROM warnings WHERE id = ?", (warning_id,), one=True)
        if not row:
            await error_response(interaction, "Warning not found.", ephemeral=True)
            return
        if row["guild_id"] != interaction.guild_id:
            await error_response(interaction, "Wrong guild.", ephemeral=True)
            return
        if not has_perm(interaction, "moderate_members", "administrator"):
            await error_response(interaction, "Missing permissions.")
            return
        await self.bot.db.execute("DELETE FROM warnings WHERE id = ?", (warning_id,))
        await self.log_action(interaction.guild_id, "unwarn", row["user_id"], interaction.user.id, f"Removed warning #{warning_id}")
        await interaction.response.send_message("Warning removed.")

    @app_commands.command(name="timeout", description="Timeout a user")
    @app_commands.describe(user="User", minutes="Minutes", reason="Reason")
    async def timeout(self, interaction: discord.Interaction, user: discord.Member, minutes: int, reason: str = "No reason provided."):
        if not has_perm(interaction, "moderate_members", "administrator"):
            await error_response(interaction, "Missing permissions.")
            return
        if not hierarchy_ok(interaction.user, user):
            await error_response(interaction, "Role hierarchy too low.")
            return
        duration = discord.utils.parse_time(f"{minutes}m")
        await user.timeout(duration, reason=reason)
        await self.log_action(interaction.guild_id, "timeout", user.id, interaction.user.id, reason, minutes * 60)
        await interaction.response.send_message(f"Timed out {user.mention} for {minutes} minutes.")

    @app_commands.command(name="untimeout", description="Remove timeout from a user")
    @app_commands.describe(user="User")
    async def untimeout(self, interaction: discord.Interaction, user: discord.Member):
        if not has_perm(interaction, "moderate_members", "administrator"):
            await error_response(interaction, "Missing permissions.")
            return
        await user.timeout(None)
        await self.log_action(interaction.guild_id, "untimeout", user.id, interaction.user.id, "Timeout removed")
        await interaction.response.send_message(f"Timeout removed from {user.mention}.")

    @app_commands.command(name="kick", description="Kick a user")
    @app_commands.describe(user="User", reason="Reason")
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided."):
        if not has_perm(interaction, "kick_members", "administrator"):
            await error_response(interaction, "Missing permissions.")
            return
        if not hierarchy_ok(interaction.user, user):
            await error_response(interaction, "Role hierarchy too low.")
            return
        await user.kick(reason=reason)
        await self.log_action(interaction.guild_id, "kick", user.id, interaction.user.id, reason)
        await interaction.response.send_message(f"Kicked {user.mention}.")

    @app_commands.command(name="ban", description="Ban a user")
    @app_commands.describe(user="User ID or mention", reason="Reason")
    async def ban(self, interaction: discord.Interaction, user: discord.User, reason: str = "No reason provided."):
        if not has_perm(interaction, "ban_members", "administrator"):
            await error_response(interaction, "Missing permissions.")
            return
        member = interaction.guild.get_member(user.id)
        if member and not hierarchy_ok(interaction.user, member):
            await error_response(interaction, "Role hierarchy too low.")
            return
        await interaction.guild.ban(user, reason=reason)
        await self.log_action(interaction.guild_id, "ban", user.id, interaction.user.id, reason)
        await interaction.response.send_message(f"Banned {user.mention}.")

    @app_commands.command(name="unban", description="Unban a user")
    @app_commands.describe(user_id="User ID")
    async def unban(self, interaction: discord.Interaction, user_id: str):
        if not has_perm(interaction, "ban_members", "administrator"):
            await error_response(interaction, "Missing permissions.")
            return
        try:
            uid = int(user_id)
        except ValueError:
            await error_response(interaction, "Invalid user ID.", ephemeral=True)
            return
        user = await self.bot.fetch_user(uid)
        await interaction.guild.unban(user)
        await self.log_action(interaction.guild_id, "unban", user.id, interaction.user.id, "Unbanned")
        await interaction.response.send_message(f"Unbanned {user.mention}.")

    @app_commands.command(name="softban", description="Softban a user (ban then unban)")
    @app_commands.describe(user="User", reason="Reason")
    async def softban(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided."):
        if not has_perm(interaction, "ban_members", "administrator"):
            await error_response(interaction, "Missing permissions.")
            return
        if not hierarchy_ok(interaction.user, user):
            await error_response(interaction, "Role hierarchy too low.")
            return
        await interaction.guild.ban(user, reason=reason, delete_message_days=7)
        await interaction.guild.unban(user)
        await self.log_action(interaction.guild_id, "softban", user.id, interaction.user.id, reason)
        await interaction.response.send_message(f"Softbanned {user.mention}.")

    @app_commands.command(name="purge", description="Delete messages")
    @app_commands.describe(count="Number of messages")
    async def purge(self, interaction: discord.Interaction, count: int):
        if not has_perm(interaction, "manage_messages", "administrator"):
            await error_response(interaction, "Missing permissions.")
            return
        await interaction.response.defer()
        deleted = await interaction.channel.purge(limit=count)
        await interaction.followup.send(f"Deleted {len(deleted)} messages.", ephemeral=True)

    @app_commands.command(name="lock", description="Lock a channel")
    @app_commands.describe(channel="Channel to lock")
    async def lock(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        if not has_perm(interaction, "manage_channels", "administrator"):
            await error_response(interaction, "Missing permissions.")
            return
        channel = channel or interaction.channel
        await channel.set_permissions(interaction.guild.default_role, send_messages=False)
        row = await self.bot.db.fetch("SELECT * FROM server_config WHERE guild_id = ?", (interaction.guild_id,), one=True)
        if not row:
            await self.bot.db.execute("INSERT INTO server_config (guild_id) VALUES (?)", (interaction.guild_id,))
        import json
        locked = json.loads(row.get("locked_channels", "[]")) if row else []
        if channel.id not in locked:
            locked.append(channel.id)
        await self.bot.db.execute(
            "UPDATE server_config SET locked_channels = ? WHERE guild_id = ?",
            (json.dumps(locked), interaction.guild_id)
        )
        await interaction.response.send_message(f"Locked {channel.mention}.")

    @app_commands.command(name="unlock", description="Unlock a channel")
    @app_commands.describe(channel="Channel to unlock")
    async def unlock(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        if not has_perm(interaction, "manage_channels", "administrator"):
            await error_response(interaction, "Missing permissions.")
            return
        channel = channel or interaction.channel
        await channel.set_permissions(interaction.guild.default_role, send_messages=None)
        row = await self.bot.db.fetch("SELECT * FROM server_config WHERE guild_id = ?", (interaction.guild_id,), one=True)
        if row:
            import json
            locked = json.loads(row.get("locked_channels", "[]"))
            if channel.id in locked:
                locked.remove(channel.id)
            await self.bot.db.execute(
                "UPDATE server_config SET locked_channels = ? WHERE guild_id = ?",
                (json.dumps(locked), interaction.guild_id)
            )
        await interaction.response.send_message(f"Unlocked {channel.mention}.")

    @app_commands.command(name="slowmode", description="Set slowmode")
    @app_commands.describe(channel="Channel", seconds="Seconds")
    async def slowmode(self, interaction: discord.Interaction, channel: discord.TextChannel = None, seconds: int = 0):
        if not has_perm(interaction, "manage_channels", "administrator"):
            await error_response(interaction, "Missing permissions.")
            return
        channel = channel or interaction.channel
        await channel.edit(slowmode_delay=seconds)
        row = await self.bot.db.fetch("SELECT * FROM server_config WHERE guild_id = ?", (interaction.guild_id,), one=True)
        if not row:
            await self.bot.db.execute("INSERT INTO server_config (guild_id) VALUES (?)", (interaction.guild_id,))
        await self.bot.db.execute(
            "UPDATE server_config SET slowmode_channel_id = ?, slowmode_seconds = ? WHERE guild_id = ?",
            (channel.id, seconds, interaction.guild_id)
        )
        await interaction.response.send_message(f"Slowmode set to {seconds}s in {channel.mention}.")

    @app_commands.command(name="nick", description="Change a user's nickname")
    @app_commands.describe(user="User", nickname="New nickname")
    async def nick(self, interaction: discord.Interaction, user: discord.Member, nickname: str = None):
        if not has_perm(interaction, "manage_nicknames", "administrator"):
            await error_response(interaction, "Missing permissions.")
            return
        if not hierarchy_ok(interaction.user, user):
            await error_response(interaction, "Role hierarchy too low.")
            return
        try:
            await user.edit(nick=nickname)
            await self.log_action(interaction.guild_id, "nick", user.id, interaction.user.id, f"Set nickname to: {nickname}")
            await interaction.response.send_message(f"Updated nickname for {user.mention}.")
        except discord.Forbidden:
            await error_response(interaction, "Missing permissions.", ephemeral=True)

    @app_commands.command(name="history", description="User moderation history")
    @app_commands.describe(user="User")
    async def history(self, interaction: discord.Interaction, user: discord.Member):
        rows = await self.bot.db.fetch(
            "SELECT * FROM moderation_actions WHERE target_id = ? AND guild_id = ? ORDER BY id DESC LIMIT 20",
            (user.id, interaction.guild_id)
        )
        if not rows:
            await interaction.response.send_message("No history.")
            return
        lines = [f"{r['action']} by <@{r['moderator_id']}>: {r['reason']} ({r['created_at'][:10]})" for r in rows]
        await interaction.response.send_message("\n".join(lines))

    @app_commands.command(name="cases", description="View recent moderation cases")
    @app_commands.describe(user="User (optional)")
    async def cases(self, interaction: discord.Interaction, user: discord.Member = None):
        if user:
            rows = await self.bot.db.fetch(
                "SELECT * FROM moderation_actions WHERE target_id = ? AND guild_id = ? ORDER BY id DESC LIMIT 20",
                (user.id, interaction.guild_id)
            )
        else:
            rows = await self.bot.db.fetch(
                "SELECT * FROM moderation_actions WHERE guild_id = ? ORDER BY id DESC LIMIT 20",
                (interaction.guild_id,)
            )
        if not rows:
            await interaction.response.send_message("No cases found.")
            return
        lines = [f"#{r['id']} {r['action']} <@{r['target_id']}> by <@{r['moderator_id']}>: {r['reason']} ({r['created_at'][:10]})" for r in rows]
        await interaction.response.send_message("\n".join(lines))
