import discord
from discord import app_commands
from discord.ext import commands
from sentinel.utils import utcnow_iso, has_perm, is_dangerous_role, safe_send
from sentinel.errors import error_response
from sentinel.embeds import success_embed, error_embed
from sentinel.config import AUTOMOD_DEFAULTS
import re
import time
from collections import defaultdict


class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.recent_messages: dict[int, list[tuple[float, str]]] = defaultdict(list)
        self.join_timestamps: dict[int, list[float]] = defaultdict(list)
        self.mention_counts: dict[int, int] = defaultdict(int)
        self.exempt_users: set[int] = set()
        self._config_cache: dict[int, dict] = {}
        self._whitelist_cache: dict[int, set[int]] = defaultdict(set)

    async def _load_config(self, guild_id: int) -> dict:
        if guild_id not in self._config_cache:
            row = await self.bot.db.fetch(
                "SELECT * FROM automod_config WHERE guild_id = ?", (guild_id,), one=True
            )
            if not row:
                await self.bot.db.execute(
                    "INSERT INTO automod_config (guild_id) VALUES (?)", (guild_id,)
                )
                self._config_cache[guild_id] = dict(AUTOMOD_DEFAULTS)
            else:
                self._config_cache[guild_id] = dict(row)
        return self._config_cache[guild_id]

    async def _load_whitelist(self, guild_id: int):
        if guild_id not in self._whitelist_cache:
            rows = await self.bot.db.fetch(
                "SELECT entity_id FROM automod_whitelist WHERE guild_id = ?",
                (guild_id,)
            )
            self._whitelist_cache[guild_id] = {r["entity_id"] for r in rows}

    async def _is_exempt(self, member: discord.Member) -> bool:
        guild_id = member.guild.id
        if member.id in self.exempt_users:
            return True
        whitelist = self._whitelist_cache.get(guild_id, set())
        if member.id in whitelist:
            return True
        for role in member.roles:
            if role.id in whitelist:
                return True
        return False

    async def process_join(self, member: discord.Member):
        guild_id = member.guild.id
        await self._load_whitelist(guild_id)
        if await self._is_exempt(member):
            return
        config = await self._load_config(guild_id)
        if not config.get("enabled"):
            return
        now = time.time()
        self.join_timestamps[guild_id].append(now)
        cutoff = now - 60
        self.join_timestamps[guild_id] = [t for t in self.join_timestamps[guild_id] if t > cutoff]
        if len(self.join_timestamps[guild_id]) >= 10:
            await self.bot.db.execute(
                "INSERT INTO automod_events (guild_id, user_id, event_type, details, created_at) VALUES (?, ?, ?, ?, ?)",
                (guild_id, member.id, "join_spike", "10+ joins in 60s", utcnow_iso())
            )
            channel = member.guild.system_channel or member.guild.text_channels[0]
            await safe_send(channel, "Raid detected: rapid join spike. Enabling lockdown.")

    async def process_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        guild_id = message.guild.id
        await self._load_whitelist(guild_id)
        if await self._is_exempt(message.author):
            return
        config = await self._load_config(guild_id)
        if not config.get("enabled"):
            return
        now = time.time()
        content = message.content or ""
        user_id = message.author.id
        events = []

        # Spam / flooding
        self.recent_messages[user_id].append((now, content))
        cutoff = now - config.get("spam_window", 10)
        self.recent_messages[user_id] = [(t, m) for t, m in self.recent_messages[user_id] if t > cutoff]
        if len(self.recent_messages[user_id]) > config.get("spam_threshold", 5):
            events.append("flooding")

        # Repeated messages
        repeat_window = now - config.get("repeat_window", 60)
        recent = [m for t, m in self.recent_messages[user_id] if t > repeat_window]
        if recent.count(content) >= config.get("repeat_threshold", 3):
            events.append("repeated_messages")

        # Excessive mentions
        if len(message.mentions) >= config.get("mention_threshold", 5):
            events.append("mass_mentions")
            self.mention_counts[user_id] += 1

        # Caps
        letters = re.sub(r"[^a-zA-Z]", "", content)
        if len(letters) > 10:
            caps_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
            if caps_ratio >= config.get("caps_threshold", 0.7):
                events.append("excessive_caps")

        # Emojis
        emoji_pattern = re.compile(
            r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0000FE0F]"
        )
        emoji_count = len(emoji_pattern.findall(content))
        if len(content) > 0 and (emoji_count / len(content)) >= config.get("emoji_threshold", 0.5):
            events.append("excessive_emojis")

        # Banned words
        banned_words = ["scam", "phishing", "malware", "gore", "nsfw"]
        lowered = content.lower()
        for word in banned_words:
            if word in lowered:
                events.append("banned_word")
                break

        # Invites
        invite_pattern = re.compile(r"discord\.gg/[^\s]+|discordapp\.com/invite/[^\s]+|discord\.com/invite/[^\s]+", re.IGNORECASE)
        for match in invite_pattern.finditer(content):
            invite = match.group(0)
            whitelisted = False
            for role in message.author.roles:
                if role.id in self._whitelist_cache.get(guild_id, set()):
                    whitelisted = True
                    break
            if not whitelisted:
                events.append("invite_link")
                break

        # Suspicious links
        link_pattern = re.compile(r"https?://\S+", re.IGNORECASE)
        for link in link_pattern.finditer(content):
            if re.search(r"(verify|login|account|steam|free.*nitro|prize)", link.group(0), re.IGNORECASE):
                events.append("suspicious_link")
                break

        if events:
            for event in events:
                await self.bot.db.execute(
                    "INSERT INTO automod_events (guild_id, user_id, event_type, details, created_at) VALUES (?, ?, ?, ?, ?)",
                    (guild_id, user_id, event, f"channel_id={message.channel.id}", utcnow_iso())
                )
            action = config.get("invite_action", "delete") if "invite_link" in events else config.get("word_action", "delete")
            if action == "delete":
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass
            await safe_send(message.channel, f"AutoMod: {message.author.mention} your message was removed ({', '.join(events)}).", delete_after=15)

    @app_commands.command(name="automod-status", description="Show AutoMod status and recent events")
    async def automod_status(self, interaction: discord.Interaction):
        if not has_perm(interaction, "administrator", "manage_guild"):
            await error_response(interaction, "Missing permissions.")
            return
        config = await self._load_config(interaction.guild_id)
        events = await self.bot.db.fetch(
            "SELECT event_type, COUNT(*) as count FROM automod_events WHERE guild_id = ? GROUP BY event_type",
            (interaction.guild_id,)
        )
        lines = [f"{e['event_type']}: {e['count']}" for e in events]
        lines.append(f"\n**Enabled:** {bool(config.get('enabled'))}")
        lines.append(f"Spam threshold: {config.get('spam_threshold')}")
        lines.append(f"Repeat threshold: {config.get('repeat_threshold')}")
        lines.append(f"Mention threshold: {config.get('mention_threshold')}")
        lines.append(f"Caps threshold: {config.get('caps_threshold')}")
        lines.append(f"Emoji threshold: {config.get('emoji_threshold')}")
        await interaction.response.send_message("\n".join(lines) if lines else "No AutoMod events recorded.")

    @app_commands.command(name="automod-whitelist", description="Whitelist a user or role")
    @app_commands.describe(entity="User or role to whitelist")
    async def automod_whitelist(self, interaction: discord.Interaction, entity: discord.Member = None, role: discord.Role = None):
        if not has_perm(interaction, "administrator", "manage_guild"):
            await error_response(interaction, "Missing permissions.")
            return
        guild_id = interaction.guild_id
        target = entity or (discord.Object(id=role.id) if role else None)
        if not target:
            await error_response(interaction, "Provide a user or role.", ephemeral=True)
            return
        entity_id = target.id
        await self.bot.db.execute(
            "INSERT OR IGNORE INTO automod_whitelist (guild_id, entity_id, entity_type) VALUES (?, ?, ?)",
            (guild_id, entity_id, "user" if entity else "role")
        )
        if entity:
            self._whitelist_cache.setdefault(guild_id, set()).add(entity_id)
        elif role:
            self._whitelist_cache.setdefault(guild_id, set()).add(role.id)
        await interaction.response.send_message(f"Whitelisted {entity.name if entity else role.name}.")

    @app_commands.command(name="automod-blacklist", description="Remove from whitelist")
    @app_commands.describe(entity="User or role to remove from whitelist")
    async def automod_blacklist(self, interaction: discord.Interaction, entity: discord.Member = None, role: discord.Role = None):
        if not has_perm(interaction, "administrator", "manage_guild"):
            await error_response(interaction, "Missing permissions.")
            return
        guild_id = interaction.guild_id
        target = entity or (discord.Object(id=role.id) if role else None)
        if not target:
            await error_response(interaction, "Provide a user or role.", ephemeral=True)
            return
        await self.bot.db.execute(
            "DELETE FROM automod_whitelist WHERE guild_id = ? AND entity_id = ?",
            (guild_id, target.id)
        )
        if entity:
            self._whitelist_cache.get(guild_id, set()).discard(target.id)
        elif role:
            self._whitelist_cache.get(guild_id, set()).discard(role.id)
        await interaction.response.send_message(f"Removed {entity.name if entity else role.name} from whitelist.")

    @app_commands.command(name="automod-thresholds", description="Update AutoMod thresholds")
    @app_commands.describe(
        spam_threshold="Spam messages in window",
        spam_window="Spam window (seconds)",
        repeat_threshold="Repeated message count",
        repeat_window="Repeat window (seconds)",
        mention_threshold="Mention count",
        caps_threshold="Caps ratio",
        emoji_threshold="Emoji ratio",
    )
    async def automod_thresholds(
        self, interaction: discord.Interaction,
        spam_threshold: int = None, spam_window: int = None,
        repeat_threshold: int = None, repeat_window: int = None,
        mention_threshold: int = None, caps_threshold: float = None, emoji_threshold: float = None
    ):
        if not has_perm(interaction, "administrator", "manage_guild"):
            await error_response(interaction, "Missing permissions.")
            return
        config = await self._load_config(interaction.guild_id)
        updates = {}
        if spam_threshold is not None:
            updates["spam_threshold"] = spam_threshold
            config["spam_threshold"] = spam_threshold
        if spam_window is not None:
            updates["spam_window"] = spam_window
            config["spam_window"] = spam_window
        if repeat_threshold is not None:
            updates["repeat_threshold"] = repeat_threshold
            config["repeat_threshold"] = repeat_threshold
        if repeat_window is not None:
            updates["repeat_window"] = repeat_window
            config["repeat_window"] = repeat_window
        if mention_threshold is not None:
            updates["mention_threshold"] = mention_threshold
            config["mention_threshold"] = mention_threshold
        if caps_threshold is not None:
            updates["caps_threshold"] = caps_threshold
            config["caps_threshold"] = caps_threshold
        if emoji_threshold is not None:
            updates["emoji_threshold"] = emoji_threshold
            config["emoji_threshold"] = emoji_threshold
        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [interaction.guild_id]
            await self.bot.db.execute(
                f"UPDATE automod_config SET {set_clause} WHERE guild_id = ?", tuple(values)
            )
        self._config_cache[interaction.guild_id] = config
        await interaction.response.send_message("Thresholds updated.")
