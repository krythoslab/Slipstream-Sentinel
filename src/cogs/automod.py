from typing import List
import discord
from discord import app_commands
from discord.ext import commands
from src.utils.helpers import send_modlog
from src.utils.errors import handle_command_error
from src.utils import automod_helpers, automod_storage


class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.banned_words: List[str] = automod_storage.load_banned_words()
        self.mention_threshold = 8
        self.url_threshold = 3
        self.spam_window: dict[int, list[float]] = {}
        self.spam_threshold = 5
        self.spam_seconds = 5.0

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild or message.author == self.bot.user:
            return
        content = message.content
        if not content:
            return

        banned_matches = automod_helpers.match_banned_words(content, self.banned_words)
        if banned_matches:
            await message.delete()
            embed = discord.Embed(
                title="AutoMod: Banned Word",
                description=f"{message.author.mention} used a banned word.",
                color=discord.Color.red(),
            )
            embed.add_field(name="Trigger", value=", ".join(banned_matches))
            await send_modlog(self.bot, embed)
            return

        mentions = automod_helpers.count_mentions(content)
        if mentions >= self.mention_threshold:
            await message.delete()
            embed = discord.Embed(
                title="AutoMod: Excessive Mentions",
                description=f"{message.author.mention} mentioned too many users.",
                color=discord.Color.orange(),
            )
            embed.add_field(name="Mentions", value=str(mentions))
            await send_modlog(self.bot, embed)
            return

        urls = automod_helpers.extract_urls(content)
        if len(urls) > self.url_threshold:
            await message.delete()
            embed = discord.Embed(
                title="AutoMod: Suspicious Links",
                description=f"{message.author.mention} posted too many links.",
                color=discord.Color.orange(),
            )
            embed.add_field(name="URLs", value="\n".join(urls[:5]))
            await send_modlog(self.bot, embed)
            return

    @app_commands.command(name="automod_add", description="Add a banned word")
    async def automod_add(self, interaction: discord.Interaction, word: str) -> None:
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        word = word.lower()
        if word in self.banned_words:
            await interaction.response.send_message("Word already banned.", ephemeral=True)
            return
        self.banned_words.append(word)
        automod_storage.save_banned_words(self.banned_words)
        await interaction.response.send_message(f"Added banned word: {word}")

    @app_commands.command(name="automod_remove", description="Remove a banned word")
    async def automod_remove(self, interaction: discord.Interaction, word: str) -> None:
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        word = word.lower()
        if word not in self.banned_words:
            await interaction.response.send_message("Word not in banned list.", ephemeral=True)
            return
        self.banned_words.remove(word)
        automod_storage.save_banned_words(self.banned_words)
        await interaction.response.send_message(f"Removed banned word: {word}")

    @app_commands.command(name="automod_list", description="List banned words")
    async def automod_list(self, interaction: discord.Interaction) -> None:
        if not self.banned_words:
            await interaction.response.send_message("No banned words configured.", ephemeral=True)
            return
        await interaction.response.send_message(", ".join(self.banned_words), ephemeral=True)
