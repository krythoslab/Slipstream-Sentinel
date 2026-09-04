from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands


class SlipstreamError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message


async def handle_command_error(interaction: discord.Interaction, error: Exception) -> None:
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"Command on cooldown. Retry in {error.retry_after:.1f}s", ephemeral=True
        )
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("Missing permissions.", ephemeral=True)
    elif isinstance(error, app_commands.BotMissingPermissions):
        await interaction.response.send_message(
            "I lack required permissions for this action.", ephemeral=True
        )
    else:
        try:
            await interaction.response.send_message(
                f"An error occurred: {error}", ephemeral=True
            )
        except Exception:
            pass
