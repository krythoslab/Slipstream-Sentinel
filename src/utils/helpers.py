from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands


async def get_modlog_channel(bot: commands.Bot) -> Optional[discord.TextChannel]:
    from src.bot import MODLOG_CHANNEL_ID
    channel = bot.get_channel(MODLOG_CHANNEL_ID)
    if isinstance(channel, discord.TextChannel):
        return channel
    return None


async def send_modlog(bot: commands.Bot, embed: discord.Embed) -> None:
    channel = await get_modlog_channel(bot)
    if channel:
        await channel.send(embed=embed)


async def check_hierarchy(
    interaction: discord.Interaction, target: discord.Member
) -> bool:
    if target.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message(
            "You cannot act on a member with equal or higher role.", ephemeral=True
        )
        return False
    if target.top_role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "I cannot act on a member with equal or higher role than me.", ephemeral=True
        )
        return False
    return True


async def ensure_mod_permissions(interaction: discord.Interaction) -> bool:
    perms = interaction.user.guild_permissions
    if not (perms.kick_members or perms.ban_members or perms.manage_messages or perms.moderate_members):
        await interaction.response.send_message(
            "You lack moderator permissions.", ephemeral=True
        )
        return False
    return True
