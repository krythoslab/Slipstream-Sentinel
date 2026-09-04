import os
import sys
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

import discord
from discord import app_commands
from discord.ext import commands

from src.config import (
    DISCORD_TOKEN,
    CLIENT_ID,
    GUILD_ID,
    WELCOME_CHANNEL_ID,
    MODLOG_CHANNEL_ID,
    DATA_DIR,
    MODLOG_DB_FILE,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True
INTENTS.moderation = True

PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)


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
        except Exception as exc:
            self.logger.error("Failed to initialize database: %s", exc)

    async def setup_hook(self) -> None:
        await self.load_extension("src.cogs.admin")
        await self.load_extension("src.cogs.moderation")
        await self.load_extension("src.cogs.automod")
        await self.load_extension("src.cogs.welcome")
        await self.load_extension("src.cogs.info")
        if not self._synced:
            try:
                guild = discord.Object(id=GUILD_ID)
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

    async def on_error(self, event: str, *args, **kwargs) -> None:
        self.logger.exception("Error in event %s", event)


def run() -> None:
    from src.config import validate
    validate()
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN not set")
    bot = SlipstreamBot()
    bot.run(DISCORD_TOKEN, reconnect=True, log_handler=None)
