import os
import sys
import math
import json
import sqlite3
import logging
import asyncio
import re
import time
import platform
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

import discord
from discord import app_commands
from discord.ext import commands, tasks

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
CLIENT_ID: str = os.getenv("CLIENT_ID", "1545238354302607450")
GUILD_ID: str = os.getenv("GUILD_ID", "1545179492815741059")

WELCOME_CHANNEL_ID: int = int(os.getenv("WELCOME_CHANNEL_ID", "0") or "0")
LEAVE_CHANNEL_ID: int = int(os.getenv("LEAVE_CHANNEL_ID", "0") or "0")
MODLOG_CHANNEL_ID: int = int(os.getenv("MODLOG_CHANNEL_ID", "0") or "0")
ANNOUNCEMENT_CHANNEL_ID: int = int(os.getenv("ANNOUNCEMENT_CHANNEL_ID", "0") or "0")
AUTOMOD_ALERT_CHANNEL_ID: int = int(os.getenv("AUTOMOD_ALERT_CHANNEL_ID", "0") or "0")

AUTOMOD_MENTION_THRESHOLD: int = int(os.getenv("AUTOMOD_MENTION_THRESHOLD", "8"))
AUTOMOD_URL_THRESHOLD: int = int(os.getenv("AUTOMOD_URL_THRESHOLD", "3"))
AUTOMOD_SPAM_THRESHOLD: int = int(os.getenv("AUTOMOD_SPAM_THRESHOLD", "5"))
AUTOMOD_SPAM_WINDOW: float = float(os.getenv("AUTOMOD_SPAM_WINDOW", "5.0"))
AUTOMOD_RAID_THRESHOLD: int = int(os.getenv("AUTOMOD_RAID_THRESHOLD", "10"))
AUTOMOD_RAID_WINDOW: float = float(os.getenv("AUTOMOD_RAID_WINDOW", "60.0"))

DATA_DIR: Path = PROJECT_ROOT / "data"
BANNED_WORDS_FILE: Path = DATA_DIR / "banned_words.json"
MODLOG_DB_FILE: Path = DATA_DIR / "modlog.db"


def validate() -> None:
    for var in ("DISCORD_TOKEN", "CLIENT_ID", "GUILD_ID"):
        if not os.getenv(var):
            raise RuntimeError(f"Missing required environment variable: {var}")


# ---------------------------------------------------------------------------
# Config storage
# ---------------------------------------------------------------------------
CONFIG_FILE = DATA_DIR / "config.json"


def _config_load() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _config_save(data: dict[str, Any]) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def config_get(key: str, default: Any = None) -> Any:
    return _config_load().get(key, default)


def config_set(key: str, value: Any) -> None:
    data = _config_load()
    data[key] = value
    _config_save(data)


def get_welcome_channel_id() -> int:
    return int(config_get("welcome_channel_id", 0) or 0)


def set_welcome_channel_id(channel_id: int) -> None:
    config_set("welcome_channel_id", channel_id)


def get_leave_channel_id() -> int:
    return int(config_get("leave_channel_id", 0) or 0)


def set_leave_channel_id(channel_id: int) -> None:
    config_set("leave_channel_id", channel_id)


def get_modlog_channel_id() -> int:
    return int(config_get("modlog_channel_id", 0) or 0)


def set_modlog_channel_id(channel_id: int) -> None:
    config_set("modlog_channel_id", channel_id)


def get_announcement_channel_id() -> int:
    return int(config_get("announcement_channel_id", 0) or 0)


def set_announcement_channel_id(channel_id: int) -> None:
    config_set("announcement_channel_id", channel_id)


def get_automod_alert_channel_id() -> int:
    return int(config_get("automod_alert_channel_id", 0) or 0)


def set_automod_alert_channel_id(channel_id: int) -> None:
    config_set("automod_alert_channel_id", channel_id)


def get_welcome_message() -> str:
    return str(config_get("welcome_message", "Welcome to {server}, {user}! Please review the rules and introduce yourself."))


def set_welcome_message(message: str) -> None:
    config_set("welcome_message", message)


def get_leave_message() -> str:
    return str(config_get("leave_message", "{user} has left {server}. We hope to see you again!"))


def set_leave_message(message: str) -> None:
    config_set("leave_message", message)


def get_automod_mention_threshold(default: int = 8) -> int:
    return int(config_get("automod_mention_threshold", default) or default)


def set_automod_mention_threshold(value: int) -> None:
    config_set("automod_mention_threshold", value)


def get_automod_url_threshold(default: int = 3) -> int:
    return int(config_get("automod_url_threshold", default) or default)


def set_automod_url_threshold(value: int) -> None:
    config_set("automod_url_threshold", value)


def get_automod_spam_threshold(default: int = 5) -> int:
    return int(config_get("automod_spam_threshold", default) or default)


def set_automod_spam_threshold(value: int) -> None:
    config_set("automod_spam_threshold", value)


def get_automod_spam_window(default: float = 5.0) -> float:
    return float(config_get("automod_spam_window", default) or default)


def set_automod_spam_window(value: float) -> None:
    config_set("automod_spam_window", value)


def get_automod_raid_threshold(default: int = 10) -> int:
    return int(config_get("automod_raid_threshold", default) or default)


def set_automod_raid_threshold(value: int) -> None:
    config_set("automod_raid_threshold", value)


def get_automod_raid_window(default: float = 60.0) -> float:
    return float(config_get("automod_raid_window", default) or default)


def set_automod_raid_window(value: float) -> None:
    config_set("automod_raid_window", value)


def is_staff_member(user_id: int) -> bool:
    return bool(config_get("staff_ids", {}).get(str(user_id), False))


def add_staff_member(user_id: int) -> None:
    data = _config_load()
    staff = data.get("staff_ids", {})
    staff[str(user_id)] = True
    data["staff_ids"] = staff
    _config_save(data)


def remove_staff_member(user_id: int) -> None:
    data = _config_load()
    staff = data.get("staff_ids", {})
    staff.pop(str(user_id), None)
    data["staff_ids"] = staff
    _config_save(data)


def get_exempt_channel_ids() -> list[int]:
    return [int(c) for c in config_get("exempt_channel_ids", [])]


def add_exempt_channel(channel_id: int) -> None:
    data = _config_load()
    exempt = [int(c) for c in data.get("exempt_channel_ids", [])]
    if channel_id not in exempt:
        exempt.append(channel_id)
    data["exempt_channel_ids"] = exempt
    _config_save(data)


def remove_exempt_channel(channel_id: int) -> None:
    data = _config_load()
    exempt = [int(c) for c in data.get("exempt_channel_ids", [])]
    if channel_id in exempt:
        exempt.remove(channel_id)
    data["exempt_channel_ids"] = exempt
    _config_save(data)


def get_exempt_role_ids() -> list[int]:
    return [int(r) for r in config_get("exempt_role_ids", [])]


def add_exempt_role(role_id: int) -> None:
    data = _config_load()
    exempt = [int(r) for r in data.get("exempt_role_ids", [])]
    if role_id not in exempt:
        exempt.append(role_id)
    data["exempt_role_ids"] = exempt
    _config_save(data)


def remove_exempt_role(role_id: int) -> None:
    data = _config_load()
    exempt = [int(r) for r in data.get("exempt_role_ids", [])]
    if role_id in exempt:
        exempt.remove(role_id)
    data["exempt_role_ids"] = exempt
    _config_save(data)


# ---------------------------------------------------------------------------
# Automod storage
# ---------------------------------------------------------------------------
def load_banned_words() -> List[str]:
    if not BANNED_WORDS_FILE.exists():
        BANNED_WORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
        BANNED_WORDS_FILE.write_text(json.dumps([]), encoding="utf-8")
        return []
    try:
        data = json.loads(BANNED_WORDS_FILE.read_text(encoding="utf-8"))
        return [w.lower() for w in data if isinstance(w, str)]
    except Exception:
        return []


def save_banned_words(words: List[str]) -> None:
    BANNED_WORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    BANNED_WORDS_FILE.write_text(
        json.dumps(list(set(w.lower() for w in words)), indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Automod helpers
# ---------------------------------------------------------------------------
URL_PATTERN = re.compile(
    r"(https?://\S+|discord\.gg/\S+|discord\.com/invite/\S+)", re.IGNORECASE
)
MENTION_PATTERN = re.compile(r"<@!?\d{10,}>", re.IGNORECASE)


def extract_urls(text: str) -> List[str]:
    return URL_PATTERN.findall(text)


def count_mentions(text: str) -> int:
    return len(MENTION_PATTERN.findall(text))


def match_banned_words(text: str, banned: List[str]) -> List[str]:
    lowered = text.lower()
    return [w for w in banned if re.search(rf"\b{re.escape(w)}\b", lowered)]


def is_spam(messages: List[Tuple[float, str]], threshold: int = 5, window_seconds: float = 5.0) -> bool:
    if len(messages) < threshold:
        return False
    if window_seconds <= 0:
        return len(messages) >= threshold
    return (messages[-1][0] - messages[0][0]) <= window_seconds


class SpamTracker:
    def __init__(self) -> None:
        self._user_messages: Dict[int, List[Tuple[float, str]]] = {}

    def record(self, user_id: int, content: str) -> None:
        now = time.monotonic()
        history = self._user_messages.setdefault(user_id, [])
        history.append((now, content))
        cutoff = now - 60.0
        self._user_messages[user_id] = [(t, c) for t, c in history if t > cutoff]

    def check(
        self, user_id: int, threshold: int, window_seconds: float
    ) -> Tuple[bool, List[Tuple[float, str]]]:
        history = self._user_messages.get(user_id, [])
        if not history:
            return False, []
        recent = [(t, c) for t, c in history if (history[-1][0] - t) <= window_seconds]
        return is_spam(recent, threshold=threshold, window_seconds=window_seconds), recent


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def get_modlog_channel(bot: commands.Bot) -> Optional[discord.TextChannel]:
    channel = bot.get_channel(MODLOG_CHANNEL_ID)
    if isinstance(channel, discord.TextChannel):
        return channel
    return None


async def send_modlog(bot: commands.Bot, embed: discord.Embed) -> None:
    channel = get_modlog_channel(bot)
    if channel:
        await channel.send(embed=embed)


def log_mod_action(guild_id: int, action: str, target_id: int, moderator_id: int, reason: str) -> None:
    try:
        with sqlite3.connect(MODLOG_DB_FILE) as conn:
            conn.execute(
                "INSERT INTO mod_actions (guild_id, action, target_id, moderator_id, reason, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (guild_id, action, target_id, moderator_id, reason, datetime.now(timezone.utc).isoformat()),
            )
    except Exception:
        pass


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


# ---------------------------------------------------------------------------
# Bot class
# ---------------------------------------------------------------------------
INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True
INTENTS.moderation = True

PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)


class SlipstreamBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix="!",
            intents=INTENTS,
            application_id=CLIENT_ID,
            heartbeat_timeout=150.0,
        )
        self.start_time = datetime.now(timezone.utc)
        self.logger = get_logger("slipstream")
        self._synced = False
        self._init_db()

    def _init_db(self) -> None:
        try:
            with sqlite3.connect(MODLOG_DB_FILE) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS mod_actions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        action TEXT NOT NULL,
                        target_id INTEGER NOT NULL,
                        moderator_id INTEGER NOT NULL,
                        reason TEXT,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS warnings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        moderator_id INTEGER NOT NULL,
                        reason TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        active INTEGER NOT NULL DEFAULT 1
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS raids (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        join_count INTEGER NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS league_drivers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        team_name TEXT,
                        number INTEGER,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS league_teams (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS league_races (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        circuit TEXT,
                        date TEXT,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS league_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        race_id INTEGER NOT NULL,
                        guild_id INTEGER NOT NULL,
                        driver_id INTEGER NOT NULL,
                        position INTEGER,
                        points INTEGER DEFAULT 0,
                        time TEXT,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS race_control_cases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        incident_number TEXT NOT NULL,
                        driver_id INTEGER NOT NULL,
                        reporter_id INTEGER NOT NULL,
                        description TEXT,
                        evidence TEXT,
                        status TEXT DEFAULT 'open',
                        penalty TEXT,
                        dismissed_reason TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
        except Exception as exc:
            self.logger.error("Failed to initialize database: %s", exc)

    async def setup_hook(self) -> None:
        await self.add_cog(AdminCog(self))
        await self.add_cog(ModerationCog(self))
        await self.add_cog(AutoModCog(self))
        await self.add_cog(WelcomeCog(self))
        await self.add_cog(InfoCog(self))
        await self.add_cog(ConfigCog(self))
        await self.add_cog(AnnouncementsCog(self))
        await self.add_cog(RolesCog(self))
        await self.add_cog(InfoServerCog(self))
        await self.add_cog(PollsCog(self))
        await self.add_cog(LeagueCog(self))
        await self.add_cog(RaceControlCog(self))
        await self.add_cog(AutomationCog(self))
        if not self._synced:
            try:
                guild = discord.Object(id=int(GUILD_ID))
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                self._synced = True
                self.logger.info("Synced slash commands to guild %s", GUILD_ID)
            except Exception as exc:
                self.logger.error("Command sync failed: %s", exc)

    async def on_ready(self) -> None:
        if self.user is None:
            self.logger.error("Bot user is None in on_ready")
            return
        self.logger.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        try:
            cmds = [c.name for c in self.tree.get_commands()]
            self.logger.info("Registered commands: %s", cmds)
        except Exception as exc:
            self.logger.error("Failed to list commands: %s", exc)

    async def on_error(self, event: str, *args, **kwargs) -> None:
        self.logger.exception("Error in event %s", event)

    async def on_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        self.logger.exception("App command error: %s", error)
        if not interaction.response.is_done():
            try:
                await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Cog: Admin
# ---------------------------------------------------------------------------
class AdminCog(commands.GroupCog, name="admin"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    @app_commands.command(name="reload", description="Reload a cog")
    async def reload(self, interaction: discord.Interaction, cog: str) -> None:
        if not await ensure_mod_permissions(interaction):
            return
        try:
            await self.bot.reload_extension(f"src.cogs.{cog}")
            await interaction.response.send_message(f"Reloaded cog: {cog}")
        except Exception as exc:
            await interaction.response.send_message(f"Failed to reload: {exc}", ephemeral=True)


# ---------------------------------------------------------------------------
# Cog: Moderation
# ---------------------------------------------------------------------------
class ModerationCog(commands.GroupCog, name="mod"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    @app_commands.command(name="warn", description="Warn a member")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "No reason provided") -> None:
        if not await ensure_mod_permissions(interaction):
            return
        if not await check_hierarchy(interaction, member):
            return
        with sqlite3.connect(MODLOG_DB_FILE) as conn:
            conn.execute(
                "INSERT INTO warnings (guild_id, user_id, moderator_id, reason, created_at) VALUES (?, ?, ?, ?, ?)",
                (interaction.guild_id, member.id, interaction.user.id, reason, datetime.now(timezone.utc).isoformat()),
            )
        log_mod_action(interaction.guild_id, "warn", member.id, interaction.user.id, reason)
        embed = discord.Embed(
            title="Warn Issued",
            description=f"{member.mention} has been warned.",
            color=discord.Color.yellow(),
        )
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="unwarn", description="Remove the latest warning from a member")
    async def unwarn(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "No reason provided") -> None:
        if not await ensure_mod_permissions(interaction):
            return
        if not await check_hierarchy(interaction, member):
            return
        with sqlite3.connect(MODLOG_DB_FILE) as conn:
            cursor = conn.execute(
                "SELECT id FROM warnings WHERE guild_id = ? AND user_id = ? AND active = 1 ORDER BY created_at DESC LIMIT 1",
                (interaction.guild_id, member.id),
            )
            row = cursor.fetchone()
            if not row:
                await interaction.response.send_message("No active warnings found for this member.", ephemeral=True)
                return
            conn.execute("UPDATE warnings SET active = 0 WHERE id = ?", (row[0],))
        log_mod_action(interaction.guild_id, "unwarn", member.id, interaction.user.id, reason)
        embed = discord.Embed(
            title="Warning Removed",
            description=f"Latest warning removed from {member.mention}.",
            color=discord.Color.green(),
        )
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="warnings", description="List warnings for a member")
    async def warnings(self, interaction: discord.Interaction, member: discord.Member) -> None:
        if not await ensure_mod_permissions(interaction):
            return
        with sqlite3.connect(MODLOG_DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT reason, created_at, active FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC LIMIT 20",
                (interaction.guild_id, member.id),
            ).fetchall()
        if not rows:
            await interaction.response.send_message("No warnings found.", ephemeral=True)
            return
        lines = []
        for row in rows:
            status = "Active" if row["active"] else "Removed"
            lines.append(f"- **{row['reason']}** ({row['created_at'][:10]}) — {status}")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.describe(minutes="Duration in minutes (max 40320)")
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: Optional[str] = "No reason provided") -> None:
        if not await ensure_mod_permissions(interaction):
            return
        if not await check_hierarchy(interaction, member):
            return
        duration = timedelta(minutes=min(minutes, 40320))
        await member.timeout(duration, reason=reason)
        log_mod_action(interaction.guild_id, "timeout", member.id, interaction.user.id, reason)
        embed = discord.Embed(
            title="Timeout Applied",
            description=f"{member.mention} has been timed out for {minutes} minute(s).",
            color=discord.Color.orange(),
        )
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="untimeout", description="Remove timeout from a member")
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "No reason provided") -> None:
        if not await ensure_mod_permissions(interaction):
            return
        if not await check_hierarchy(interaction, member):
            return
        await member.timeout(None, reason=reason)
        log_mod_action(interaction.guild_id, "untimeout", member.id, interaction.user.id, reason)
        embed = discord.Embed(
            title="Timeout Removed",
            description=f"Timeout removed from {member.mention}.",
            color=discord.Color.green(),
        )
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="kick", description="Kick a member")
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "No reason provided") -> None:
        if not await ensure_mod_permissions(interaction):
            return
        if not await check_hierarchy(interaction, member):
            return
        await member.kick(reason=reason)
        log_mod_action(interaction.guild_id, "kick", member.id, interaction.user.id, reason)
        embed = discord.Embed(
            title="Member Kicked",
            description=f"{member.mention} has been kicked.",
            color=discord.Color.red(),
        )
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="ban", description="Ban a member")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "No reason provided") -> None:
        if not await ensure_mod_permissions(interaction):
            return
        if not await check_hierarchy(interaction, member):
            return
        await member.ban(reason=reason)
        log_mod_action(interaction.guild_id, "ban", member.id, interaction.user.id, reason)
        embed = discord.Embed(
            title="Member Banned",
            description=f"{member.mention} has been banned.",
            color=discord.Color.dark_red(),
        )
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="unban", description="Unban a user")
    @app_commands.describe(user_id="The user ID to unban")
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: Optional[str] = "No reason provided") -> None:
        if not await ensure_mod_permissions(interaction):
            return
        try:
            user_id_int = int(user_id)
        except ValueError:
            await interaction.response.send_message("Invalid user ID.", ephemeral=True)
            return
        user = discord.Object(id=user_id_int)
        try:
            await interaction.guild.unban(user, reason=reason)
        except discord.NotFound:
            await interaction.response.send_message("User not found in ban list.", ephemeral=True)
            return
        log_mod_action(interaction.guild_id, "unban", user_id_int, interaction.user.id, reason)
        embed = discord.Embed(
            title="User Unbanned",
            description=f"User ID {user_id} has been unbanned.",
            color=discord.Color.green(),
        )
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="purge", description="Purge messages")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    async def purge(self, interaction: discord.Interaction, amount: int) -> None:
        if not await ensure_mod_permissions(interaction):
            return
        if not interaction.channel or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Run this in a text channel.", ephemeral=True)
            return
        amount = max(1, min(amount, 100))
        deleted = await interaction.channel.purge(limit=amount)
        log_mod_action(interaction.guild_id, "purge", 0, interaction.user.id, f"Purged {len(deleted)} messages in channel {interaction.channel_id}")
        await interaction.response.send_message(f"Deleted {len(deleted)} message(s).", ephemeral=True)
        embed = discord.Embed(
            title="Messages Purged",
            description=f"Deleted {len(deleted)} message(s) in {interaction.channel.mention}.",
            color=discord.Color.purple(),
        )
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await send_modlog(self.bot, embed)

    @app_commands.command(name="lock", description="Lock a channel")
    async def lock(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None) -> None:
        if not await ensure_mod_permissions(interaction):
            return
        target = channel or (interaction.channel if isinstance(interaction.channel, discord.TextChannel) else None)
        if not target:
            await interaction.response.send_message("Specify a text channel.", ephemeral=True)
            return
        overwrite = target.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await target.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        log_mod_action(interaction.guild_id, "lock", 0, interaction.user.id, f"Locked channel {target.id}")
        embed = discord.Embed(
            title="Channel Locked",
            description=f"{target.mention} has been locked.",
            color=discord.Color.dark_red(),
        )
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="unlock", description="Unlock a channel")
    async def unlock(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None) -> None:
        if not await ensure_mod_permissions(interaction):
            return
        target = channel or (interaction.channel if isinstance(interaction.channel, discord.TextChannel) else None)
        if not target:
            await interaction.response.send_message("Specify a text channel.", ephemeral=True)
            return
        overwrite = target.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None
        await target.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        log_mod_action(interaction.guild_id, "unlock", 0, interaction.user.id, f"Unlocked channel {target.id}")
        embed = discord.Embed(
            title="Channel Unlocked",
            description=f"{target.mention} has been unlocked.",
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="slowmode", description="Set channel slowmode")
    @app_commands.describe(seconds="Delay in seconds (0-21600, 0 to disable)")
    async def slowmode(self, interaction: discord.Interaction, seconds: int, channel: Optional[discord.TextChannel] = None) -> None:
        if not await ensure_mod_permissions(interaction):
            return
        target = channel or (interaction.channel if isinstance(interaction.channel, discord.TextChannel) else None)
        if not target:
            await interaction.response.send_message("Specify a text channel.", ephemeral=True)
            return
        seconds = max(0, min(seconds, 21600))
        await target.edit(slowmode_delay=seconds)
        log_mod_action(interaction.guild_id, "slowmode", 0, interaction.user.id, f"Set slowmode to {seconds}s in channel {target.id}")
        embed = discord.Embed(
            title="Slowmode Updated",
            description=f"Slowmode set to {seconds} second(s) in {target.mention}.",
            color=discord.Color.orange(),
        )
        embed.set_footer(text=f"Moderator: {interaction.user}")
        await interaction.response.send_message(embed=embed)
        await send_modlog(self.bot, embed)

    @app_commands.command(name="history", description="View moderation history for a user")
    @app_commands.describe(user="The user to view history for")
    async def history(self, interaction: discord.Interaction, user: discord.User) -> None:
        if not await ensure_mod_permissions(interaction):
            return
        try:
            with sqlite3.connect(MODLOG_DB_FILE) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT action, reason, created_at FROM mod_actions WHERE guild_id = ? AND target_id = ? ORDER BY created_at DESC LIMIT 20",
                    (interaction.guild_id, user.id),
                ).fetchall()
        except Exception:
            rows = []
        if not rows:
            await interaction.response.send_message("No moderation history found.", ephemeral=True)
            return
        lines = []
        for row in rows:
            lines.append(f"- **{row['action']}**: {row.get('reason', 'No reason')} ({row['created_at'][:10]})")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)


# ---------------------------------------------------------------------------
# Cog: AutoMod
# ---------------------------------------------------------------------------
class AutoModCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.banned_words: List[str] = load_banned_words()
        self.mention_threshold = get_automod_mention_threshold()
        self.url_threshold = get_automod_url_threshold()
        self.spam_threshold = get_automod_spam_threshold()
        self.spam_seconds = get_automod_spam_window()
        self.raid_threshold = get_automod_raid_threshold()
        self.raid_seconds = get_automod_raid_window()
        self.spam_tracker = SpamTracker()
        self.user_offenses: dict[int, int] = {}
        self.recent_message_hashes: dict[int, List[tuple[float, str]]] = {}

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    def _is_exempt(self, member: discord.Member, channel: discord.abc.GuildChannel) -> bool:
        if is_staff_member(member.id):
            return True
        if member.id in [r.id for r in member.roles if r.id in get_exempt_role_ids()]:
            return True
        if channel.id in get_exempt_channel_ids():
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
            with sqlite3.connect(MODLOG_DB_FILE) as conn:
                conn.execute(
                    "INSERT INTO raids (guild_id, join_count, created_at) VALUES (?, ?, ?)",
                    (guild_id, 1, now),
                )
        except Exception:
            pass

        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.raid_seconds)
        try:
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

        banned_matches = match_banned_words(content, self.banned_words)
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

        mentions = count_mentions(content)
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

        urls = extract_urls(content)
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
        is_spam_flag, recent = self.spam_tracker.check(
            message.author.id,
            threshold=self.spam_threshold,
            window_seconds=self.spam_seconds,
        )
        if is_spam_flag:
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
        save_banned_words(self.banned_words)
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
        save_banned_words(self.banned_words)
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
                add_exempt_channel(target_id_int)
                await interaction.response.send_message(f"Added exempt channel: {target_id_int}")
            elif target_type == "role":
                add_exempt_role(target_id_int)
                await interaction.response.send_message(f"Added exempt role: {target_id_int}")
            else:
                await interaction.response.send_message("Invalid target type. Use channel or role.", ephemeral=True)
        elif action == "remove":
            if target_type == "channel":
                remove_exempt_channel(target_id_int)
                await interaction.response.send_message(f"Removed exempt channel: {target_id_int}")
            elif target_type == "role":
                remove_exempt_role(target_id_int)
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
                    set_automod_mention_threshold(int(value))
                    self.mention_threshold = int(value)
                    await interaction.response.send_message(f"mention_threshold set to {value}")
                elif setting == "url_threshold":
                    set_automod_url_threshold(int(value))
                    self.url_threshold = int(value)
                    await interaction.response.send_message(f"url_threshold set to {value}")
                elif setting == "spam_threshold":
                    set_automod_spam_threshold(int(value))
                    self.spam_threshold = int(value)
                    await interaction.response.send_message(f"spam_threshold set to {value}")
                elif setting == "spam_window":
                    set_automod_spam_window(float(value))
                    self.spam_seconds = float(value)
                    await interaction.response.send_message(f"spam_window set to {value}")
                elif setting == "raid_threshold":
                    set_automod_raid_threshold(int(value))
                    self.raid_threshold = int(value)
                    await interaction.response.send_message(f"raid_threshold set to {value}")
                elif setting == "raid_window":
                    set_automod_raid_window(float(value))
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


# ---------------------------------------------------------------------------
# Cog: Welcome
# ---------------------------------------------------------------------------
class WelcomeCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        channel_id = get_welcome_channel_id()
        if not channel_id:
            return
        channel = self.bot.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        message_template = get_welcome_message()
        content = message_template.replace("{server}", member.guild.name).replace("{user}", member.display_name)
        embed = discord.Embed(
            title=f"Welcome to {member.guild.name}, {member.display_name}!",
            description=content,
            color=discord.Color.blue(),
        )
        embed.add_field(name="Members", value=str(member.guild.member_count))
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Slipstream Motorsport")
        await channel.send(content=member.mention, embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        channel_id = get_leave_channel_id()
        if not channel_id:
            return
        channel = self.bot.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        message_template = get_leave_message()
        content = message_template.replace("{server}", member.guild.name).replace("{user}", member.display_name)
        embed = discord.Embed(
            title=f"Goodbye, {member.display_name}!",
            description=content,
            color=discord.Color.red(),
        )
        embed.set_footer(text="Slipstream Motorsport")
        await channel.send(embed=embed)

    @app_commands.command(name="welcome_set", description="Set the welcome channel for this server")
    async def welcome_set(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permissions.", ephemeral=True)
            return
        set_welcome_channel_id(channel.id)
        await interaction.response.send_message(f"Welcome channel set to {channel.mention}")

    @app_commands.command(name="leave_set", description="Set the leave channel for this server")
    async def leave_set(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permissions.", ephemeral=True)
            return
        set_leave_channel_id(channel.id)
        await interaction.response.send_message(f"Leave channel set to {channel.mention}")

    @app_commands.command(name="welcome_message_set", description="Set the welcome message template")
    async def welcome_message_set(self, interaction: discord.Interaction, message: str) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permissions.", ephemeral=True)
            return
        set_welcome_message(message)
        await interaction.response.send_message("Welcome message updated. Use {server} and {user} as placeholders.")

    @app_commands.command(name="leave_message_set", description="Set the leave message template")
    async def leave_message_set(self, interaction: discord.Interaction, message: str) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permissions.", ephemeral=True)
            return
        set_leave_message(message)
        await interaction.response.send_message("Leave message updated. Use {server} and {user} as placeholders.")


# ---------------------------------------------------------------------------
# Cog: Info
# ---------------------------------------------------------------------------
def _latency_ms(bot: commands.Bot) -> str:
    latency = bot.latency
    if isinstance(latency, float) and (math.isnan(latency) or math.isinf(latency)):
        return "unknown"
    return str(round(latency * 1000))


class InfoCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        logger = get_logger("slipstream.info")
        logger.exception("Error in Info cog command: %s", error)
        await handle_command_error(interaction, error)

    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"Pong! {_latency_ms(self.bot)} ms")

    @app_commands.command(name="about", description="Bot information")
    async def about(self, interaction: discord.Interaction) -> None:
        bot: SlipstreamBot = self.bot
        uptime = datetime.now(timezone.utc) - bot.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        embed = discord.Embed(
            title="Slipstream Sentinel",
            description="Production-ready Discord bot for Slipstream Motorsport.",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Latency", value=f"{_latency_ms(self.bot)} ms")
        embed.add_field(name="Uptime", value=f"{hours}h {minutes}m")
        embed.add_field(name="Python", value=platform.python_version())
        embed.add_field(name="Discord.py", value=discord.__version__)
        embed.set_footer(text="Slipstream Motorsport")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="help", description="Show available commands")
    async def help(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="Slipstream Sentinel - Command Help",
            description="Use slash commands to interact with the bot.",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="General", value="/ping, /about, /help, /status", inline=False)
        embed.add_field(name="Moderation (/mod)", value="/mod warn, /mod unwarn, /mod warnings, /mod timeout, /mod untimeout, /mod kick, /mod ban, /mod unban, /mod purge, /mod lock, /mod unlock, /mod slowmode, /mod history", inline=False)
        embed.add_field(name="AutoMod", value="/automod_add, /automod_remove, /automod_list, /automod exempt, /automod config", inline=False)
        embed.add_field(name="Welcome", value="/welcome_set, /leave_set, /welcome_message_set, /leave_message_set", inline=False)
        embed.add_field(name="Config", value="/config", inline=False)
        embed.add_field(name="Announcements", value="/announce", inline=False)
        embed.add_field(name="Polls", value="/poll", inline=False)
        embed.add_field(name="Roles", value="/role", inline=False)
        embed.add_field(name="Info", value="/serverinfo, /userinfo", inline=False)
        embed.add_field(name="Admin", value="/admin reload", inline=False)
        embed.set_footer(text="Slipstream Motorsport")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="status", description="Set the bot's activity status")
    @app_commands.describe(activity="The activity to set (playing, watching, listening, streaming)", text="The status text")
    async def status(self, interaction: discord.Interaction, activity: str, text: str) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You need Manage Server permissions.", ephemeral=True)
            return
        activity_type_map = {
            "playing": discord.ActivityType.playing,
            "watching": discord.ActivityType.watching,
            "listening": discord.ActivityType.listening,
            "streaming": discord.ActivityType.streaming,
        }
        activity_type = activity_type_map.get(activity.lower())
        if activity_type is None:
            await interaction.response.send_message("Invalid activity type. Use: playing, watching, listening, streaming", ephemeral=True)
            return
        await self.bot.change_presence(activity=discord.Activity(type=activity_type, name=text))
        await interaction.response.send_message(f"Status set to {activity} {text}")


# ---------------------------------------------------------------------------
# Cog: Config
# ---------------------------------------------------------------------------
class ConfigCog(commands.GroupCog, name="config"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    @app_commands.command(name="welcome_channel", description="Set the welcome channel")
    async def config_welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        set_welcome_channel_id(channel.id)
        await interaction.response.send_message(f"Welcome channel set to {channel.mention}")

    @app_commands.command(name="leave_channel", description="Set the leave channel")
    async def config_leave_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        set_leave_channel_id(channel.id)
        await interaction.response.send_message(f"Leave channel set to {channel.mention}")

    @app_commands.command(name="modlog_channel", description="Set the modlog channel")
    async def config_modlog_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        set_modlog_channel_id(channel.id)
        await interaction.response.send_message(f"Modlog channel set to {channel.mention}")

    @app_commands.command(name="announcement_channel", description="Set the announcement channel")
    async def config_announcement_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        set_announcement_channel_id(channel.id)
        await interaction.response.send_message(f"Announcement channel set to {channel.mention}")

    @app_commands.command(name="automod_alert_channel", description="Set the AutoMod alert channel")
    async def config_automod_alert_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        set_automod_alert_channel_id(channel.id)
        await interaction.response.send_message(f"AutoMod alert channel set to {channel.mention}")

    @app_commands.command(name="welcome_message", description="Set the welcome message template")
    async def config_welcome_message(self, interaction: discord.Interaction, message: str) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        set_welcome_message(message)
        await interaction.response.send_message("Welcome message updated.")

    @app_commands.command(name="leave_message", description="Set the leave message template")
    async def config_leave_message(self, interaction: discord.Interaction, message: str) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        set_leave_message(message)
        await interaction.response.send_message("Leave message updated.")


# ---------------------------------------------------------------------------
# Cog: Announcements
# ---------------------------------------------------------------------------
class AnnouncementsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    @app_commands.command(name="announce", description="Send an announcement to the configured channel")
    @app_commands.describe(title="Announcement title", message="Announcement message")
    async def announce(self, interaction: discord.Interaction, title: str, message: str) -> None:
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        channel_id = get_announcement_channel_id()
        if not channel_id:
            await interaction.response.send_message("Announcement channel not configured. Use /config announcement_channel.", ephemeral=True)
            return
        channel = self.bot.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Announcement channel not found.", ephemeral=True)
            return
        embed = discord.Embed(
            title=title,
            description=message,
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"Announced by {interaction.user}")
        await channel.send(embed=embed)
        await interaction.response.send_message(f"Announcement sent to {channel.mention}")


# ---------------------------------------------------------------------------
# Cog: Roles
# ---------------------------------------------------------------------------
class RolesCog(commands.Cog):
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


# ---------------------------------------------------------------------------
# Cog: InfoServer
# ---------------------------------------------------------------------------
class InfoServerCog(commands.Cog):
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


# ---------------------------------------------------------------------------
# Cog: Polls
# ---------------------------------------------------------------------------
class PollsCog(commands.Cog):
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


# ---------------------------------------------------------------------------
# Cog: League
# ---------------------------------------------------------------------------
class LeagueCog(commands.GroupCog, name="league"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    @app_commands.command(name="register", description="Register as a driver")
    @app_commands.describe(number="Your driver number")
    async def register(self, interaction: discord.Interaction, number: int) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Missing permissions.", ephemeral=True)
            return
        try:
            with sqlite3.connect(MODLOG_DB_FILE) as conn:
                conn.execute(
                    "INSERT INTO league_drivers (guild_id, user_id, number, created_at) VALUES (?, ?, ?, ?)",
                    (interaction.guild_id, interaction.user.id, number, discord.utils.utcnow().isoformat()),
                )
            await interaction.response.send_message(f"Registered as driver #{number}")
        except Exception:
            await interaction.response.send_message("Registration failed. You may already be registered.", ephemeral=True)

    @app_commands.command(name="team", description="Set your team")
    @app_commands.describe(team_name="Your team name")
    async def team(self, interaction: discord.Interaction, team_name: str) -> None:
        with sqlite3.connect(MODLOG_DB_FILE) as conn:
            conn.execute(
                "UPDATE league_drivers SET team_name = ? WHERE guild_id = ? AND user_id = ?",
                (team_name, interaction.guild_id, interaction.user.id),
            )
        await interaction.response.send_message(f"Team set to {team_name}")

    @app_commands.command(name="standings", description="Show driver standings")
    async def standings(self, interaction: discord.Interaction) -> None:
        with sqlite3.connect(MODLOG_DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT driver_id, SUM(points) as total FROM league_results WHERE guild_id = ? GROUP BY driver_id ORDER BY total DESC LIMIT 20",
                (interaction.guild_id,),
            ).fetchall()
        if not rows:
            await interaction.response.send_message("No standings available.", ephemeral=True)
            return
        lines = [f"#{i+1} <@{row['driver_id']}> - {row['total']} pts" for i, row in enumerate(rows)]
        await interaction.response.send_message("\n".join(lines))


# ---------------------------------------------------------------------------
# Cog: RaceControl
# ---------------------------------------------------------------------------
class RaceControlCog(commands.GroupCog, name="steward"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    @app_commands.command(name="report", description="File a steward incident report")
    @app_commands.describe(driver="The driver involved", description="Incident description", evidence="Evidence link (optional)")
    async def report(self, interaction: discord.Interaction, driver: discord.Member, description: str, evidence: Optional[str] = None) -> None:
        with sqlite3.connect(MODLOG_DB_FILE) as conn:
            conn.execute(
                "INSERT INTO race_control_cases (guild_id, incident_number, driver_id, reporter_id, description, evidence, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    interaction.guild_id,
                    f"INC-{discord.utils.utcnow().timestamp():.0f}",
                    driver.id,
                    interaction.user.id,
                    description,
                    evidence or "",
                    "open",
                    discord.utils.utcnow().isoformat(),
                    discord.utils.utcnow().isoformat(),
                ),
            )
        await interaction.response.send_message(f"Incident report filed against {driver.mention}")

    @app_commands.command(name="cases", description="List open steward cases")
    async def cases(self, interaction: discord.Interaction) -> None:
        with sqlite3.connect(MODLOG_DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT incident_number, driver_id, description, status FROM race_control_cases WHERE guild_id = ? AND status = 'open' ORDER BY created_at DESC",
                (interaction.guild_id,),
            ).fetchall()
        if not rows:
            await interaction.response.send_message("No open cases.", ephemeral=True)
            return
        lines = [f"{row['incident_number']} - <@{row['driver_id']}>: {row['description'][:50]}" for row in rows]
        await interaction.response.send_message("\n".join(lines))

    @app_commands.command(name="close", description="Close a steward case")
    @app_commands.describe(incident_number="The incident number", penalty="Penalty (optional)", reason="Dismissal reason (if no penalty)")
    async def close(self, interaction: discord.Interaction, incident_number: str, penalty: Optional[str] = None, reason: Optional[str] = None) -> None:
        with sqlite3.connect(MODLOG_DB_FILE) as conn:
            if penalty:
                conn.execute(
                    "UPDATE race_control_cases SET status = 'penalized', penalty = ?, updated_at = ? WHERE incident_number = ? AND guild_id = ?",
                    (penalty, discord.utils.utcnow().isoformat(), incident_number, interaction.guild_id),
                )
            else:
                conn.execute(
                    "UPDATE race_control_cases SET status = 'dismissed', dismissed_reason = ?, updated_at = ? WHERE incident_number = ? AND guild_id = ?",
                    (reason or "No penalty", discord.utils.utcnow().isoformat(), incident_number, interaction.guild_id),
                )
        await interaction.response.send_message(f"Case {incident_number} closed.")


# ---------------------------------------------------------------------------
# Cog: Automation
# ---------------------------------------------------------------------------
class AutomationCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.reminder_loop.start()

    async def cog_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await handle_command_error(interaction, error)

    def cog_unload(self) -> None:
        self.reminder_loop.cancel()

    @tasks.loop(minutes=30)
    async def reminder_loop(self) -> None:
        now = datetime.now(timezone.utc)
        self.bot.logger.info("Automation loop running at %s", now.isoformat())

    @reminder_loop.before_loop
    async def before_reminder_loop(self) -> None:
        await self.bot.wait_until_ready()

    @app_commands.command(name="remind", description="Set a reminder")
    @app_commands.describe(seconds="Seconds until reminder", message="Reminder message")
    async def remind(self, interaction: discord.Interaction, seconds: int, message: str) -> None:
        if seconds < 1 or seconds > 86400:
            await interaction.response.send_message("Reminder must be between 1 and 86400 seconds.", ephemeral=True)
            return
        await interaction.response.send_message(f"Reminder set for {seconds} seconds.")
        await discord.utils.sleep_until(datetime.now(timezone.utc))
        try:
            await interaction.user.send(f"Reminder: {message}")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def run() -> None:
    validate()
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN not set")
    bot = SlipstreamBot()
    bot.run(DISCORD_TOKEN, reconnect=True, log_handler=None)


if __name__ == "__main__":
    run()
