from typing import List
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands
from src.utils.helpers import send_modlog, log_mod_action
from src.utils.errors import handle_command_error
from src.utils import automod_helpers, automod_storage
from src.config import (
    AUTOMOD_MENTION_THRESHOLD,
    AUTOMOD_URL_THRESHOLD,
    AUTOMOD_SPAM_THRESHOLD,
    AUTOMOD_SPAM_WINDOW,
)


class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.banned_words: List[str] = automod_storage.load_banned_words()
        self.mention_threshold = AUTOMOD_MENTION_THRESHOLD
        self.url_threshold = AUTOMOD_URL_THRESHOLD
        self.spam_threshold = AUTOMOD_SPAM_THRESHOLD
        self.spam_seconds = AUTOMOD_SPAM_WINDOW
        self.spam_tracker = automod_helpers.SpamTracker()
        self.user_offenses: dict[int, int] = {}

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    async def _escalate(self, message: discord.Message, action: str) -> None:
        guild_id = message.guild.id if message.guild else 0
        self.user_offenses[message.author.id] = self.user_offenses.get(message.author.id, 0) + 1
        offenses = self.user_offenses[message.author.id]
        embed = discord.Embed(
            title=f"AutoMod: {action}",
            description=f"{message.author.mention} triggered AutoMod ({action}).",
            color=discord.Color.red(),
        )
        embed.add_field(name="Offenses", value=str(offenses))
        embed.set_footer(text="Slipstream Sentinel AutoMod")
        await send_modlog(self.bot, embed)
        log_mod_action(guild_id, f"automod_{action.lower()}", message.author.id, self.bot.user.id, "AutoMod triggered")

        if offenses >= 3:
            try:
                duration = 60 * min(offenses - 1, 24)
                await message.author.timeout(
                    datetime.now(timezone.utc) + timedelta(minutes=duration),
                    reason="AutoMod escalation",
                )
                embed.add_field(name="Action", value=f"Timed out for {duration} minutes")
                await send_modlog(self.bot, embed)
                log_mod_action(guild_id, "automod_timeout_escalation", message.author.id, self.bot.user.id, f"AutoMod escalation: {duration}m timeout")
            except Exception:
                pass

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
            await self._escalate(message, "Banned Word")
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
            await self._escalate(message, "Excessive Mentions")
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
            await self._escalate(message, "Suspicious Links")
            return

        self.spam_tracker.record(message.author.id, content)
        is_spam, recent = self.spam_tracker.check(
            message.author.id,
            threshold=self.spam_threshold,
            window_seconds=self.spam_seconds,
        )
        if is_spam:
            await message.delete()
            embed = discord.Embed(
                title="AutoMod: Spam/Flooding",
                description=f"{message.author.mention} is spamming messages.",
                color=discord.Color.red(),
            )
            embed.add_field(name="Messages", value=str(len(recent)))
            await send_modlog(self.bot, embed)
            await self._escalate(message, "Spam/Flooding")
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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoMod(bot))
