from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from src.utils.errors import handle_command_error


class Roles(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    @app_commands.command(name="give", description="Give a role to a member")
    @app_commands.describe(member="The member to give the role to", role="The role to give")
    async def give(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role) -> None:
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        if role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("You cannot assign a role equal or higher than your own.", ephemeral=True)
            return
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message("I cannot assign a role equal or higher than mine.", ephemeral=True)
            return
        if role in member.roles:
            await interaction.response.send_message("Member already has this role.", ephemeral=True)
            return
        await member.add_roles(role, reason=f"Given by {interaction.user}")
        await interaction.response.send_message(f"Gave {role.mention} to {member.mention}")

    @app_commands.command(name="remove", description="Remove a role from a member")
    @app_commands.describe(member="The member to remove the role from", role="The role to remove")
    async def remove(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role) -> None:
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        if role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("You cannot remove a role equal or higher than your own.", ephemeral=True)
            return
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message("I cannot remove a role equal or higher than mine.", ephemeral=True)
            return
        if role not in member.roles:
            await interaction.response.send_message("Member does not have this role.", ephemeral=True)
            return
        await member.remove_roles(role, reason=f"Removed by {interaction.user}")
        await interaction.response.send_message(f"Removed {role.mention} from {member.mention}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Roles(bot))
