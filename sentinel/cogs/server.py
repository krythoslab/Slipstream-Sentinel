import discord
from discord import app_commands
from discord.ext import commands
from sentinel.utils import utcnow_iso, has_perm, safe_send, hierarchy_ok, is_dangerous_role
from sentinel.errors import error_response
from sentinel.embeds import success_embed, error_embed, info_embed


class Server(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="announce", description="Send an announcement")
    @app_commands.describe(channel="Channel to announce in", message="Announcement content")
    async def announce(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        if not has_perm(interaction, "manage_messages", "administrator"):
            await error_response(interaction, "Missing permissions.")
            return
        await safe_send(channel, f"**Announcement**\n{message}")
        await interaction.response.send_message("Announced.", ephemeral=True)

    @app_commands.command(name="role-give", description="Give a role to a user")
    @app_commands.describe(user="User", role="Role")
    async def role_give(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        if not has_perm(interaction, "manage_roles", "administrator"):
            await error_response(interaction, "Missing permissions.")
            return
        if role >= interaction.guild.me.top_role:
            await error_response(interaction, "Role is too high.")
            return
        if is_dangerous_role(role):
            await error_response(interaction, "Cannot assign dangerous roles.")
            return
        if not hierarchy_ok(interaction.user, user):
            await error_response(interaction, "Role hierarchy too low.")
            return
        try:
            await user.add_roles(role, reason=f"By {interaction.user}")
            await interaction.response.send_message(f"Gave {role.name} to {user.mention}.")
        except discord.Forbidden:
            await error_response(interaction, "Forbidden.")

    @app_commands.command(name="role-remove", description="Remove a role from a user")
    @app_commands.describe(user="User", role="Role")
    async def role_remove(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        if not has_perm(interaction, "manage_roles", "administrator"):
            await error_response(interaction, "Missing permissions.")
            return
        if role >= interaction.guild.me.top_role:
            await error_response(interaction, "Role is too high.")
            return
        if not hierarchy_ok(interaction.user, user):
            await error_response(interaction, "Role hierarchy too low.")
            return
        try:
            await user.remove_roles(role, reason=f"By {interaction.user}")
            await interaction.response.send_message(f"Removed {role.name} from {user.mention}.")
        except discord.Forbidden:
            await error_response(interaction, "Forbidden.")

    @app_commands.command(name="serverinfo", description="Server information")
    async def serverinfo(self, interaction: discord.Interaction):
        g = interaction.guild
        embed = discord.Embed(title=g.name, color=0x0099ff, timestamp=discord.utils.parse_time(utcnow_iso()))
        embed.add_field(name="Members", value=str(g.member_count), inline=True)
        embed.add_field(name="Owner", value=str(g.owner), inline=True)
        embed.add_field(name="Created", value=g.created_at.strftime("%Y-%m-%d"), inline=True)
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="User information")
    @app_commands.describe(user="User")
    async def userinfo(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        embed = discord.Embed(title=str(user), color=0x0099ff, timestamp=discord.utils.parse_time(utcnow_iso()))
        embed.add_field(name="ID", value=str(user.id), inline=True)
        embed.add_field(name="Joined", value=user.joined_at.strftime("%Y-%m-%d") if user.joined_at else "N/A", inline=True)
        embed.add_field(name="Created", value=user.created_at.strftime("%Y-%m-%d"), inline=True)
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="poll", description="Create a poll")
    @app_commands.describe(question="Poll question", option_a="Option A", option_b="Option B", option_c="Option C", option_d="Option D")
    async def poll(self, interaction: discord.Interaction, question: str, option_a: str, option_b: str, option_c: str = None, option_d: str = None):
        options = [option_a, option_b]
        if option_c:
            options.append(option_c)
        if option_d:
            options.append(option_d)
        emojis = ["🇦", "🇧", "🇨", "🇩"]
        desc = "\n".join(f"{emojis[i]} {opt}" for i, opt in enumerate(options))
        embed = discord.Embed(title=question, description=desc, color=0x0099ff, timestamp=discord.utils.parse_time(utcnow_iso()))
        msg = await safe_send(interaction.channel, embed=embed)
        if msg:
            for i in range(len(options)):
                try:
                    await msg.add_reaction(emojis[i])
                except discord.Forbidden:
                    pass
        await interaction.response.send_message("Poll created.", ephemeral=True)

    @app_commands.command(name="config", description="Server configuration")
    @app_commands.describe(action="Action", channel="Channel", message="Message", seconds="Seconds", modlog="Modlog channel")
    async def config(self, interaction: discord.Interaction, action: str, channel: discord.TextChannel = None, message: str = None, seconds: int = 0, modlog: discord.TextChannel = None):
        if not has_perm(interaction, "administrator", "manage_guild"):
            await error_response(interaction, "Missing permissions.")
            return

        guild_id = interaction.guild_id
        if action == "welcome":
            row = await self.bot.db.fetch("SELECT * FROM welcome_config WHERE guild_id = ?", (guild_id,), one=True)
            if not row:
                await self.bot.db.execute("INSERT INTO welcome_config (guild_id) VALUES (?)", (guild_id,))
            await self.bot.db.execute(
                "UPDATE welcome_config SET enabled = 1, channel_id = ?, message = ? WHERE guild_id = ?",
                (channel.id if channel else None, message, guild_id)
            )
            await interaction.response.send_message("Welcome configured.")
        elif action == "welcome-disable":
            await self.bot.db.execute("UPDATE welcome_config SET enabled = 0 WHERE guild_id = ?", (guild_id,))
            await interaction.response.send_message("Welcome disabled.")
        elif action == "set-dm-welcome":
            await self.bot.db.execute("UPDATE welcome_config SET dm_message = ? WHERE guild_id = ?", (message, guild_id))
            await interaction.response.send_message("DM welcome message set.")
        elif action == "set-modlog":
            row = await self.bot.db.fetch("SELECT * FROM server_config WHERE guild_id = ?", (guild_id,), one=True)
            if not row:
                await self.bot.db.execute("INSERT INTO server_config (guild_id) VALUES (?)", (guild_id,))
            await self.bot.db.execute(
                "UPDATE server_config SET modlog_channel_id = ? WHERE guild_id = ?",
                (modlog.id if modlog else None, guild_id)
            )
            await interaction.response.send_message("Modlog channel set.")
        else:
            await interaction.response.send_message("Unknown action.", ephemeral=True)
