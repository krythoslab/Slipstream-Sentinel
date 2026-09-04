from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta, datetime, timezone
from src.utils.helpers import (
    ensure_mod_permissions,
    check_hierarchy,
    send_modlog,
    log_mod_action,
)
from src.utils.errors import handle_command_error


class Moderation(commands.GroupCog, name="mod"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    @app_commands.command(name="warn", description="Warn a member")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "No reason provided") -> None:
        if not await ensure_mod_permissions(interaction):
            return
        if not await check_hierarchy(interaction, member):
            return
        import sqlite3
        from src.config import MODLOG_DB_FILE
        with sqlite3.connect(MODLOG_DB_FILE) as conn:
            conn.execute(
                "INSERT INTO warnings (guild_id, user_id, moderator_id, reason, created_at) VALUES (?, ?, ?, ?, ?)",
                (interaction.guild_id, member.id, interaction.user.id, reason, datetime.now(timezone.utc).isoformat()),
            )
        log_mod_action(interaction.guild_id, "warn", member.id, interaction.user.id, reason)
        embed = discord.Embed(
            title="Warn Issued",
            description=f"{member.mention} has been warned.",
            color=discord.Color.yellow(),
        )
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="unwarn", description="Remove the latest warning from a member")
    async def unwarn(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "No reason provided") -> None:
        if not await ensure_mod_permissions(interaction):
            return
        if not await check_hierarchy(interaction, member):
            return
        import sqlite3
        from src.config import MODLOG_DB_FILE
        with sqlite3.connect(MODLOG_DB_FILE) as conn:
            cursor = conn.execute(
                "SELECT id FROM warnings WHERE guild_id = ? AND user_id = ? AND active = 1 ORDER BY created_at DESC LIMIT 1",
                (interaction.guild_id, member.id),
            )
            row = cursor.fetchone()
            if not row:
                await interaction.response.send_message("No active warnings found for this member.", ephemeral=True)
                return
            conn.execute("UPDATE warnings SET active = 0 WHERE id = ?", (row[0],))
        log_mod_action(interaction.guild_id, "unwarn", member.id, interaction.user.id, reason)
        embed = discord.Embed(
            title="Warning Removed",
            description=f"Latest warning removed from {member.mention}.",
            color=discord.Color.green(),
        )
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="warnings", description="List warnings for a member")
    async def warnings(self, interaction: discord.Interaction, member: discord.Member) -> None:
        if not await ensure_mod_permissions(interaction):
            return
        import sqlite3
        from src.config import MODLOG_DB_FILE
        with sqlite3.connect(MODLOG_DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT reason, created_at, active FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC LIMIT 20",
                (interaction.guild_id, member.id),
            ).fetchall()
        if not rows:
            await interaction.response.send_message("No warnings found.", ephemeral=True)
            return
        lines = []
        for row in rows:
            status = "Active" if row["active"] else "Removed"
            lines.append(f"- **{row['reason']}** ({row['created_at'][:10]}) — {status}")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.describe(minutes="Duration in minutes (max 40320)")
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: Optional[str] = "No reason provided") -> None:
        if not await ensure_mod_permissions(interaction):
            return
        if not await check_hierarchy(interaction, member):
            return
        duration = timedelta(minutes=min(minutes, 40320))
        await member.timeout(duration, reason=reason)
        log_mod_action(interaction.guild_id, "timeout", member.id, interaction.user.id, reason)
        embed = discord.Embed(
            title="Timeout Applied",
            description=f"{member.mention} has been timed out for {minutes} minute(s).",
            color=discord.Color.orange(),
        )
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="untimeout", description="Remove timeout from a member")
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "No reason provided") -> None:
        if not await ensure_mod_permissions(interaction):
            return
        if not await check_hierarchy(interaction, member):
            return
        await member.timeout(None, reason=reason)
        log_mod_action(interaction.guild_id, "untimeout", member.id, interaction.user.id, reason)
        embed = discord.Embed(
            title="Timeout Removed",
            description=f"Timeout removed from {member.mention}.",
            color=discord.Color.green(),
        )
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="kick", description="Kick a member")
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "No reason provided") -> None:
        if not await ensure_mod_permissions(interaction):
            return
        if not await check_hierarchy(interaction, member):
            return
        await member.kick(reason=reason)
        log_mod_action(interaction.guild_id, "kick", member.id, interaction.user.id, reason)
        embed = discord.Embed(
            title="Member Kicked",
            description=f"{member.mention} has been kicked.",
            color=discord.Color.red(),
        )
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="ban", description="Ban a member")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "No reason provided") -> None:
        if not await ensure_mod_permissions(interaction):
            return
        if not await check_hierarchy(interaction, member):
            return
        await member.ban(reason=reason)
        log_mod_action(interaction.guild_id, "ban", member.id, interaction.user.id, reason)
        embed = discord.Embed(
            title="Member Banned",
            description=f"{member.mention} has been banned.",
            color=discord.Color.dark_red(),
        )
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="unban", description="Unban a user")
    @app_commands.describe(user_id="The user ID to unban")
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: Optional[str] = "No reason provided") -> None:
        if not await ensure_mod_permissions(interaction):
            return
        try:
            user_id_int = int(user_id)
        except ValueError:
            await interaction.response.send_message("Invalid user ID.", ephemeral=True)
            return
        user = discord.Object(id=user_id_int)
        try:
            await interaction.guild.unban(user, reason=reason)
        except discord.NotFound:
            await interaction.response.send_message("User not found in ban list.", ephemeral=True)
            return
        log_mod_action(interaction.guild_id, "unban", user_id_int, interaction.user.id, reason)
        embed = discord.Embed(
            title="User Unbanned",
            description=f"User ID {user_id} has been unbanned.",
            color=discord.Color.green(),
        )
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="purge", description="Purge messages")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    async def purge(self, interaction: discord.Interaction, amount: int) -> None:
        if not await ensure_mod_permissions(interaction):
            return
        if not interaction.channel or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Run this in a text channel.", ephemeral=True)
            return
        amount = max(1, min(amount, 100))
        deleted = await interaction.channel.purge(limit=amount)
        log_mod_action(interaction.guild_id, "purge", 0, interaction.user.id, f"Purged {len(deleted)} messages in channel {interaction.channel_id}")
        await interaction.response.send_message(f"Deleted {len(deleted)} message(s).", ephemeral=True)
        embed = discord.Embed(
            title="Messages Purged",
            description=f"Deleted {len(deleted)} message(s) in {interaction.channel.mention}.",
            color=discord.Color.purple(),
        )
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await send_modlog(self.bot, embed)

    @app_commands.command(name="lock", description="Lock a channel")
    async def lock(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None) -> None:
        if not await ensure_mod_permissions(interaction):
            return
        target = channel or (interaction.channel if isinstance(interaction.channel, discord.TextChannel) else None)
        if not target:
            await interaction.response.send_message("Specify a text channel.", ephemeral=True)
            return
        overwrite = target.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await target.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        log_mod_action(interaction.guild_id, "lock", 0, interaction.user.id, f"Locked channel {target.id}")
        embed = discord.Embed(
            title="Channel Locked",
            description=f"{target.mention} has been locked.",
            color=discord.Color.dark_red(),
        )
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="unlock", description="Unlock a channel")
    async def unlock(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None) -> None:
        if not await ensure_mod_permissions(interaction):
            return
        target = channel or (interaction.channel if isinstance(interaction.channel, discord.TextChannel) else None)
        if not target:
            await interaction.response.send_message("Specify a text channel.", ephemeral=True)
            return
        overwrite = target.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None
        await target.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        log_mod_action(interaction.guild_id, "unlock", 0, interaction.user.id, f"Unlocked channel {target.id}")
        embed = discord.Embed(
            title="Channel Unlocked",
            description=f"{target.mention} has been unlocked.",
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="slowmode", description="Set channel slowmode")
    @app_commands.describe(seconds="Delay in seconds (0-21600, 0 to disable)")
    async def slowmode(self, interaction: discord.Interaction, seconds: int, channel: Optional[discord.TextChannel] = None) -> None:
        if not await ensure_mod_permissions(interaction):
            return
        target = channel or (interaction.channel if isinstance(interaction.channel, discord.TextChannel) else None)
        if not target:
            await interaction.response.send_message("Specify a text channel.", ephemeral=True)
            return
        seconds = max(0, min(seconds, 21600))
        await target.edit(slowmode_delay=seconds)
        log_mod_action(interaction.guild_id, "slowmode", 0, interaction.user.id, f"Set slowmode to {seconds}s in channel {target.id}")
        embed = discord.Embed(
            title="Slowmode Updated",
            description=f"Slowmode set to {seconds} second(s) in {target.mention}.",
            color=discord.Color.orange(),
        )
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="history", description="View moderation history for a user")
    @app_commands.describe(user="The user to view history for")
    async def history(self, interaction: discord.Interaction, user: discord.User) -> None:
        if not await ensure_mod_permissions(interaction):
            return
        try:
            import sqlite3
            from src.config import MODLOG_DB_FILE
            with sqlite3.connect(MODLOG_DB_FILE) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT action, reason, created_at FROM mod_actions WHERE guild_id = ? AND target_id = ? ORDER BY created_at DESC LIMIT 20",
                    (interaction.guild_id, user.id),
                ).fetchall()
        except Exception:
            rows = []
        if not rows:
            await interaction.response.send_message("No moderation history found.", ephemeral=True)
            return
        lines = []
        for row in rows:
            lines.append(f"- **{row['action']}**: {row.get('reason', 'No reason')} ({row['created_at'][:10]})")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))