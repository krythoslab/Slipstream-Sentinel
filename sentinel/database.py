import aiosqlite
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sentinel.config import DB_PATH


class Database:
    def __init__(self, path: str):
        self.path = path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._conn.commit()

    async def close(self):
        if self._conn:
            await self._conn.close()

    async def fetch(self, query: str, params: tuple = (), one: bool = False) -> Any:
        async with self._conn.execute(query, params) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
        return rows[0] if one and rows else rows

    async def fetch_value(self, query: str, params: tuple = ()) -> Any:
        row = await self.fetch(query, params, one=True)
        return row[0] if row else None

    async def execute(self, query: str, params: tuple = ()) -> int:
        async with self._conn.execute(query, params) as cur:
            await self._conn.commit()
            return cur.lastrowid

    async def executemany(self, query: str, params_list: list) -> None:
        await self._conn.executemany(query, params_list)
        await self._conn.commit()

    async def executescript(self, script: str) -> None:
        await self._conn.executescript(script)
        await self._conn.commit()


async def init_db(db: Database):
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            display_name TEXT,
            joined_at TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS moderation_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT,
            duration_seconds INTEGER,
            channel_id INTEGER,
            message_id INTEGER,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS automod_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS welcome_config (
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            channel_id INTEGER,
            message TEXT,
            embed INTEGER DEFAULT 0,
            dm_message TEXT,
            leave_channel_id INTEGER,
            leave_message TEXT,
            leave_embed INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS server_config (
            guild_id INTEGER PRIMARY KEY,
            slowmode_channel_id INTEGER,
            slowmode_seconds INTEGER DEFAULT 0,
            locked_channels TEXT DEFAULT '[]',
            modlog_channel_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS league_drivers (
            user_id INTEGER PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            team_id INTEGER,
            number INTEGER,
            country TEXT DEFAULT 'N/A',
            joined_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS league_teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            color TEXT DEFAULT '#0099ff',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS league_races (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            circuit TEXT,
            scheduled_at TEXT NOT NULL,
            status TEXT DEFAULT 'scheduled',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS league_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            race_id INTEGER NOT NULL,
            driver_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            points INTEGER DEFAULT 0,
            dnq INTEGER DEFAULT 0,
            dnf INTEGER DEFAULT 0,
            fastest_lap INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS steward_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            reporter_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            evidence TEXT,
            status TEXT DEFAULT 'open',
            penalty TEXT,
            closed_by INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            due_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS autorole_config (
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            role_id INTEGER,
            exempt_roles TEXT DEFAULT '[]'
        );
        CREATE TABLE IF NOT EXISTS verification_config (
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            channel_id INTEGER,
            role_id INTEGER,
            min_account_age_days INTEGER DEFAULT 7
        );
        CREATE TABLE IF NOT EXISTS league_seasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS automod_config (
            guild_id INTEGER PRIMARY KEY,
            spam_threshold INTEGER DEFAULT 5,
            spam_window INTEGER DEFAULT 10,
            repeat_threshold INTEGER DEFAULT 3,
            repeat_window INTEGER DEFAULT 60,
            mention_threshold INTEGER DEFAULT 5,
            caps_threshold REAL DEFAULT 0.7,
            emoji_threshold REAL DEFAULT 0.5,
            invite_action TEXT DEFAULT 'delete',
            url_action TEXT DEFAULT 'delete',
            word_action TEXT DEFAULT 'delete',
            enabled INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS automod_whitelist (
            guild_id INTEGER NOT NULL,
            entity_id INTEGER NOT NULL,
            entity_type TEXT NOT NULL,
            PRIMARY KEY (guild_id, entity_id, entity_type)
        );
        CREATE TABLE IF NOT EXISTS poll_votes (
            poll_message_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            option_index INTEGER NOT NULL,
            PRIMARY KEY (poll_message_id, user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_mod_actions_guild ON moderation_actions(guild_id);
        CREATE INDEX IF NOT EXISTS idx_warnings_guild ON warnings(guild_id);
        CREATE INDEX IF NOT EXISTS idx_automod_events_guild ON automod_events(guild_id);
        CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(due_at);
        CREATE INDEX IF NOT EXISTS idx_steward_cases_guild ON steward_cases(guild_id);
    """)


async def migrate(db: Database):
    rows = await db.fetch("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'")
    if not rows:
        await db.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY)")
        await db.execute("INSERT INTO schema_version (version) VALUES (1)")
    else:
        row = await db.fetch("SELECT MAX(version) as v FROM schema_version", one=True)
        current = row["v"] if row else 0
        if current < 1:
            pass  # future migrations
