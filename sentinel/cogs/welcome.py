import discord
from discord import app_commands
from discord.ext import commands
from sentinel.utils import utcnow_iso, is_dangerous_role, safe_send, has_perm
from sentinel.errors import SlipstreamError, error_response
from sentinel.embeds import success_embed, error_embed


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def process_join(self, member: discord.Member):
        guild_id = member.guild.id
        row = await self.bot.db.fetch(
            "SELECT * FROM welcome_config WHERE guild_id = ?", (guild_id,), one=True
        )
        if not row or not row.get("enabled"):
            return
        if row.get("channel_id"):
            ch = member.guild.get_channel(row["channel_id"])
            if ch:
                msg = row.get("message", "Welcome {user}!").format(user=member.mention, server=member.guild.name)
                if row.get("embed"):
                    embed = discord.Embed(title="Welcome!", description=msg, color=0x0099ff, timestamp=discord.utils.parse_time(utcnow_iso()))
                    if member.avatar:
                        embed.set_thumbnail(url=member.avatar.url)
                    await safe_send(ch, embed=embed)
                else:
                    await safe_send(ch, msg)
        if row.get("dm_message"):
            try:
                await member.send(row["dm_message"].format(user=member.mention, server=member.guild.name))
            except discord.Forbidden:
                pass

    @app_commands.command(name="welcome-setup", description="Configure welcome messages")
    @app_commands.describe(channel="Welcome channel", message="Welcome message", embed="Use embeds", dm="DM welcome message")
    async def welcome_setup(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str = "Welcome {user}!", embed: bool = False, dm: str = None):
        if not has_perm(interaction, "administrator", "manage_guild"):
            await error_response(interaction, "Missing permissions.")
            return
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO welcome_config (guild_id, enabled, channel_id, message, embed, dm_message) VALUES (?, 1, ?, ?, ?, ?)",
            (interaction.guild_id, channel.id, message, int(embed), dm)
        )
        await interaction.response.send_message(embed=success_embed("Welcome configured"))

    @app_commands.command(name="welcome-enable", description="Enable welcome messages")
    async def welcome_enable(self, interaction: discord.Interaction):
        if not has_perm(interaction, "administrator", "manage_guild"):
            await error_response(interaction, "Missing permissions.")
            return
        await self.bot.db.execute(
            "UPDATE welcome_config SET enabled = 1 WHERE guild_id = ?", (interaction.guild_id,)
        )
        await interaction.response.send_message(embed=success_embed("Welcome enabled"))

    @app_commands.command(name="welcome-disable", description="Disable welcome messages")
    async def welcome_disable(self, interaction: discord.Interaction):
        if not has_perm(interaction, "administrator", "manage_guild"):
            await error_response(interaction, "Missing permissions.")
            return
        await self.bot.db.execute(
            "UPDATE welcome_config SET enabled = 0 WHERE guild_id = ?", (interaction.guild_id,)
        )
        await interaction.response.send_message(embed=success_embed("Welcome disabled"))

    @app_commands.command(name="welcome-test", description="Test welcome message")
    async def welcome_test(self, interaction: discord.Interaction):
        if not has_perm(interaction, "administrator", "manage_guild"):
            await error_response(interaction, "Missing permissions.")
            return
        row = await self.bot.db.fetch(
            "SELECT * FROM welcome_config WHERE guild_id = ?", (interaction.guild_id,), one=True
        )
        if not row or not row.get("enabled") or not row.get("channel_id"):
            await error_response(interaction, "Welcome not configured/enabled.", ephemeral=True)
            return
        ch = interaction.guild.get_channel(row["channel_id"])
        if not ch:
            await error_response(interaction, "Channel not found.", ephemeral=True)
            return
        msg = row.get("message", "Welcome {user}!").format(user=interaction.user.mention, server=interaction.guild.name)
        if row.get("embed"):
            embed = discord.Embed(title="Welcome!", description=msg, color=0x0099ff, timestamp=discord.utils.parse_time(utcnow_iso()))
            if interaction.user.avatar:
                embed.set_thumbnail(url=interaction.user.avatar.url)
            await safe_send(ch, embed=embed)
        else:
            await safe_send(ch, msg)
        await interaction.response.send_message("Welcome test sent.", ephemeral=True)
