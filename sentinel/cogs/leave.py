import discord
from discord import app_commands
from discord.ext import commands
from sentinel.utils import utcnow_iso, is_dangerous_role, safe_send, has_perm
from sentinel.errors import SlipstreamError, error_response
from sentinel.embeds import success_embed, error_embed


class Leave(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def process_leave(self, member: discord.Member):
        guild_id = member.guild.id
        row = await self.bot.db.fetch(
            "SELECT * FROM welcome_config WHERE guild_id = ?", (guild_id,), one=True
        )
        if not row or not row.get("enabled") or not row.get("leave_channel_id"):
            return
        ch = member.guild.get_channel(row["leave_channel_id"])
        if not ch:
            return
        msg = row.get("leave_message", "{user} has left.").format(user=member.mention, server=member.guild.name)
        if row.get("leave_embed"):
            embed = discord.Embed(title="Goodbye!", description=msg, color=0xff0000, timestamp=discord.utils.parse_time(utcnow_iso()))
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            await safe_send(ch, embed=embed)
        else:
            await safe_send(ch, msg)

    @app_commands.command(name="leave-setup", description="Configure leave messages")
    @app_commands.describe(channel="Leave channel", message="Leave message", embed="Use embeds")
    async def leave_setup(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str = "{user} has left.", embed: bool = False):
        if not has_perm(interaction, "administrator", "manage_guild"):
            await error_response(interaction, "Missing permissions.")
            return
        await self.bot.db.execute(
            "UPDATE welcome_config SET leave_channel_id = ?, leave_message = ?, leave_embed = ? WHERE guild_id = ?",
            (channel.id, message, int(embed), interaction.guild_id)
        )
        await interaction.response.send_message(embed=success_embed("Leave configured"))

    @app_commands.command(name="leave-enable", description="Enable leave messages")
    async def leave_enable(self, interaction: discord.Interaction):
        if not has_perm(interaction, "administrator", "manage_guild"):
            await error_response(interaction, "Missing permissions.")
            return
        await self.bot.db.execute(
            "UPDATE welcome_config SET enabled = 1 WHERE guild_id = ?", (interaction.guild_id,)
        )
        await interaction.response.send_message(embed=success_embed("Leave enabled"))

    @app_commands.command(name="leave-disable", description="Disable leave messages")
    async def leave_disable(self, interaction: discord.Interaction):
        if not has_perm(interaction, "administrator", "manage_guild"):
            await error_response(interaction, "Missing permissions.")
            return
        await self.bot.db.execute(
            "UPDATE welcome_config SET enabled = 0 WHERE guild_id = ?", (interaction.guild_id,)
        )
        await interaction.response.send_message(embed=success_embed("Leave disabled"))

    @app_commands.command(name="leave-test", description="Test leave message")
    async def leave_test(self, interaction: discord.Interaction):
        if not has_perm(interaction, "administrator", "manage_guild"):
            await error_response(interaction, "Missing permissions.")
            return
        row = await self.bot.db.fetch(
            "SELECT * FROM welcome_config WHERE guild_id = ?", (interaction.guild_id,), one=True
        )
        if not row or not row.get("enabled") or not row.get("leave_channel_id"):
            await error_response(interaction, "Leave not configured/enabled.", ephemeral=True)
            return
        ch = interaction.guild.get_channel(row["leave_channel_id"])
        if not ch:
            await error_response(interaction, "Channel not found.", ephemeral=True)
            return
        msg = row.get("leave_message", "{user} has left.").format(user=interaction.user.mention, server=interaction.guild.name)
        if row.get("leave_embed"):
            embed = discord.Embed(title="Goodbye!", description=msg, color=0xff0000, timestamp=discord.utils.parse_time(utcnow_iso()))
            if interaction.user.avatar:
                embed.set_thumbnail(url=interaction.user.avatar.url)
            await safe_send(ch, embed=embed)
        else:
            await safe_send(ch, msg)
        await interaction.response.send_message("Leave test sent.", ephemeral=True)
