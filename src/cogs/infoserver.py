from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from src.utils.errors import handle_command_error


class InfoServer(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    @app_commands.command(name="serverinfo", description="Show server information")
    async def serverinfo(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        embed = discord.Embed(
            title=guild.name,
            color=discord.Color.blurple(),
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Server ID", value=guild.id)
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown")
        embed.add_field(name="Members", value=guild.member_count)
        embed.add_field(name="Text Channels", value=len(guild.text_channels))
        embed.add_field(name="Voice Channels", value=len(guild.voice_channels))
        embed.add_field(name="Roles", value=len(guild.roles))
        embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Show user information")
    @app_commands.describe(user="The user to show info for")
    async def userinfo(self, interaction: discord.Interaction, user: Optional[discord.Member] = None) -> None:
        target = user or interaction.user
        if not isinstance(target, discord.Member):
            await interaction.response.send_message("User not found in this server.", ephemeral=True)
            return
        embed = discord.Embed(
            title=target.display_name,
            color=discord.Color.blurple(),
        )
        if target.avatar:
            embed.set_thumbnail(url=target.avatar.url)
        embed.add_field(name="User ID", value=target.id)
        embed.add_field(name="Username", value=str(target))
        embed.add_field(name="Joined", value=target.joined_at.strftime("%Y-%m-%d") if target.joined_at else "Unknown")
        embed.add_field(name="Roles", value=", ".join(r.mention for r in target.roles) or "None")
        embed.add_field(name="Top Role", value=target.top_role.mention)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(InfoServer(bot))
