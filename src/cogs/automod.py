from typing import List, Optional
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands
from src.utils.helpers import send_modlog, log_mod_action
from src.utils.errors import handle_command_error
from src.utils import automod_helpers, automod_storage
from src.modules import config_storage


class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.banned_words: List[str] = automod_storage.load_banned_words()
        self.mention_threshold = config_storage.get_automod_mention_threshold()
        self.url_threshold = config_storage.get_automod_url_threshold()
        self.spam_threshold = config_storage.get_automod_spam_threshold()
        self.spam_seconds = config_storage.get_automod_spam_window()
        self.raid_threshold = config_storage.get_automod_raid_threshold()
        self.raid_seconds = config_storage.get_automod_raid_window()
        self.spam_tracker = automod_helpers.SpamTracker()
        self.user_offenses: dict[int, int] = {}
        self.recent_message_hashes: dict[int, List[tuple[float, str]]] = {}

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    def _is_exempt(self, member: discord.Member, channel: discord.abc.GuildChannel) -> bool:
        if config_storage.is_staff_member(member.id):
            return True
        if member.id in [r.id for r in member.roles if r.id in config_storage.get_exempt_role_ids()]:
            return True
        if channel.id in config_storage.get_exempt_channel_ids():
            return True
        return False

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
    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot:
            return
        guild_id = member.guild.id
        now = datetime.now(timezone.utc).isoformat()
        try:
            import sqlite3
            from src.config import MODLOG_DB_FILE
            with sqlite3.connect(MODLOG_DB_FILE) as conn:
                conn.execute(
                    "INSERT INTO raids (guild_id, join_count, created_at) VALUES (?, ?, ?)",
                    (guild_id, 1, now),
                )
        except Exception:
            pass

        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.raid_seconds)
        try:
            import sqlite3
            from src.config import MODLOG_DB_FILE
            with sqlite3.connect(MODLOG_DB_FILE) as conn:
                rows = conn.execute(
                    "SELECT COUNT(*) FROM raids WHERE guild_id = ? AND created_at >= ?",
                    (guild_id, cutoff.isoformat()),
                ).fetchone()
                count = rows[0] if rows else 0
        except Exception:
            count = 0

        if count >= self.raid_threshold:
            embed = discord.Embed(
                title="AutoMod: Raid Detected",
                description=f"Raid detected! {count} joins in the last {self.raid_seconds}s.",
                color=discord.Color.dark_red(),
            )
            await send_modlog(self.bot, embed)
            log_mod_action(guild_id, "automod_raid", member.id, self.bot.user.id, f"Raid detected: {count} joins")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild or message.author == self.bot.user:
            return
        if not isinstance(message.channel, discord.TextChannel):
            return

        if self._is_exempt(message.author, message.channel):
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

        user_history = self.recent_message_hashes.setdefault(message.author.id, [])
        msg_hash = hash(content.strip().lower())
        user_history.append((datetime.now(timezone.utc).timestamp(), msg_hash))
        cutoff = datetime.now(timezone.utc).timestamp() - 60.0
        user_history[:] = [(t, h) for t, h in user_history if t > cutoff]
        same_message_count = sum(1 for _, h in user_history if h == msg_hash)
        if same_message_count >= 4:
            await message.delete()
            embed = discord.Embed(
                title="AutoMod: Repeated Messages",
                description=f"{message.author.mention} is sending repeated messages.",
                color=discord.Color.orange(),
            )
            embed.add_field(name="Repeats", value=str(same_message_count))
            await send_modlog(self.bot, embed)
            await self._escalate(message, "Repeated Messages")
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

    @app_commands.command(name="automod_exempt", description="Manage AutoMod exemptions")
    @app_commands.describe(action="add or remove", target_type="channel or role", target_id="ID of the channel or role")
    async def automod_exempt(self, interaction: discord.Interaction, action: str, target_type: str, target_id: str) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        try:
            target_id_int = int(target_id)
        except ValueError:
            await interaction.response.send_message("Invalid ID.", ephemeral=True)
            return
        if action == "add":
            if target_type == "channel":
                config_storage.add_exempt_channel(target_id_int)
                await interaction.response.send_message(f"Added exempt channel: {target_id_int}")
            elif target_type == "role":
                config_storage.add_exempt_role(target_id_int)
                await interaction.response.send_message(f"Added exempt role: {target_id_int}")
            else:
                await interaction.response.send_message("Invalid target type. Use channel or role.", ephemeral=True)
        elif action == "remove":
            if target_type == "channel":
                config_storage.remove_exempt_channel(target_id_int)
                await interaction.response.send_message(f"Removed exempt channel: {target_id_int}")
            elif target_type == "role":
                config_storage.remove_exempt_role(target_id_int)
                await interaction.response.send_message(f"Removed exempt role: {target_id_int}")
            else:
                await interaction.response.send_message("Invalid target type. Use channel or role.", ephemeral=True)
        else:
            await interaction.response.send_message("Invalid action. Use add or remove.", ephemeral=True)

    @app_commands.command(name="automod_config", description="View or update AutoMod thresholds")
    @app_commands.describe(setting="threshold to update", value="new value")
    async def automod_config(self, interaction: discord.Interaction, setting: Optional[str] = None, value: Optional[str] = None) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        if setting and value:
            try:
                if setting == "mention_threshold":
                    config_storage.set_automod_mention_threshold(int(value))
                    self.mention_threshold = int(value)
                    await interaction.response.send_message(f"mention_threshold set to {value}")
                elif setting == "url_threshold":
                    config_storage.set_automod_url_threshold(int(value))
                    self.url_threshold = int(value)
                    await interaction.response.send_message(f"url_threshold set to {value}")
                elif setting == "spam_threshold":
                    config_storage.set_automod_spam_threshold(int(value))
                    self.spam_threshold = int(value)
                    await interaction.response.send_message(f"spam_threshold set to {value}")
                elif setting == "spam_window":
                    config_storage.set_automod_spam_window(float(value))
                    self.spam_seconds = float(value)
                    await interaction.response.send_message(f"spam_window set to {value}")
                elif setting == "raid_threshold":
                    config_storage.set_automod_raid_threshold(int(value))
                    self.raid_threshold = int(value)
                    await interaction.response.send_message(f"raid_threshold set to {value}")
                elif setting == "raid_window":
                    config_storage.set_automod_raid_window(float(value))
                    self.raid_seconds = float(value)
                    await interaction.response.send_message(f"raid_window set to {value}")
                else:
                    await interaction.response.send_message("Unknown setting.", ephemeral=True)
            except ValueError:
                await interaction.response.send_message("Invalid value type.", ephemeral=True)
        else:
            embed = discord.Embed(
                title="AutoMod Configuration",
                color=discord.Color.blurple(),
            )
            embed.add_field(name="mention_threshold", value=str(self.mention_threshold))
            embed.add_field(name="url_threshold", value=str(self.url_threshold))
            embed.add_field(name="spam_threshold", value=str(self.spam_threshold))
            embed.add_field(name="spam_window", value=f"{self.spam_seconds}s")
            embed.add_field(name="raid_threshold", value=str(self.raid_threshold))
            embed.add_field(name="raid_window", value=f"{self.raid_seconds}s")
            await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoMod(bot))
