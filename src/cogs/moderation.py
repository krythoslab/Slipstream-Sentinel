from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
from src.utils.helpers import (
    ensure_mod_permissions,
    check_hierarchy,
    send_modlog,
)
from src.utils.errors import handle_command_error


class Moderation(commands.GroupCog, name="mod"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._history: dict[int, list[dict]] = {}

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    def _add_history(self, guild_id: int, entry: dict) -> None:
        self._history.setdefault(guild_id, []).append(entry)

    @app_commands.command(name="warn", description="Warn a member")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "No reason provided") -> None:
        if not await ensure_mod_permissions(interaction):
            return
        if not await check_hierarchy(interaction, member):
            return
        self._add_history(interaction.guild_id, {"action": "warn", "user_id": member.id, "reason": reason})
        embed = discord.Embed(
            title="Warn Issued",
            description=f"{member.mention} has been warned.",
            color=discord.Color.yellow(),
        )
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.describe(minutes="Duration in minutes (max 40320)")
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: Optional[str] = "No reason provided") -> None:
        if not await ensure_mod_permissions(interaction):
            return
        if not await check_hierarchy(interaction, member):
            return
        duration = timedelta(minutes=min(minutes, 40320))
        await member.timeout(duration, reason=reason)
        self._add_history(interaction.guild_id, {"action": "timeout", "user_id": member.id, "duration": minutes, "reason": reason})
        embed = discord.Embed(
            title="Timeout Applied",
            description=f"{member.mention} has been timed out for {minutes} minute(s).",
            color=discord.Color.orange(),
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
        self._add_history(interaction.guild_id, {"action": "kick", "user_id": member.id, "reason": reason})
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
        self._add_history(interaction.guild_id, {"action": "ban", "user_id": member.id, "reason": reason})
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
        self._add_history(interaction.guild_id, {"action": "unban", "user_id": user_id_int, "reason": reason})
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
        self._add_history(interaction.guild_id, {"action": "purge", "channel_id": interaction.channel_id, "amount": len(deleted)})
        await interaction.response.send_message(f"Deleted {len(deleted)} message(s).", ephemeral=True)
        embed = discord.Embed(
            title="Messages Purged",
            description=f"Deleted {len(deleted)} message(s) in {interaction.channel.mention}.",
            color=discord.Color.purple(),
        )
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await send_modlog(self.bot, embed)

    @app_commands.command(name="history", description="View moderation history for a user")
    @app_commands.describe(user="The user to view history for")
    async def history(self, interaction: discord.Interaction, user: discord.User) -> None:
        if not await ensure_mod_permissions(interaction):
            return
        entries = self._history.get(interaction.guild_id, [])
        user_entries = [e for e in entries if e.get("user_id") == user.id]
        if not user_entries:
            await interaction.response.send_message("No moderation history found.", ephemeral=True)
            return
        lines = []
        for entry in user_entries[-20:]:
            lines.append(f"- **{entry['action']}**: {entry.get('reason', 'No reason')}")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)
