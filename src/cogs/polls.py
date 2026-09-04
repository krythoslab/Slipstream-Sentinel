from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from src.utils.errors import handle_command_error


class Polls(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    @app_commands.command(name="poll", description="Create a simple poll")
    @app_commands.describe(question="The poll question", option1="Option 1", option2="Option 2", option3="Option 3 (optional)", option4="Option 4 (optional)")
    async def poll(self, interaction: discord.Interaction, question: str, option1: str, option2: str, option3: Optional[str] = None, option4: Optional[str] = None) -> None:
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        options = [option1, option2]
        if option3:
            options.append(option3)
        if option4:
            options.append(option4)
        if len(options) < 2:
            await interaction.response.send_message("At least two options are required.", ephemeral=True)
            return
        if len(options) > 4:
            await interaction.response.send_message("Maximum 4 options allowed.", ephemeral=True)
            return
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        embed = discord.Embed(
            title=question,
            description="\n".join(f"{emojis[i]} {opt}" for i, opt in enumerate(options)),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"Poll by {interaction.user}")
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        for i in range(len(options)):
            await msg.add_reaction(emojis[i])


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Polls(bot))
