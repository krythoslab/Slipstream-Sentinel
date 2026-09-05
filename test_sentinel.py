
import sqlite3
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch, MagicMock

# Set dummy token before importing sentinel
os.environ["DISCORD_TOKEN"] = "dummy_test_token"

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock discord before importing sentinel
discord_mock = MagicMock()
sys.modules['discord'] = discord_mock
sys.modules['discord.ext'] = MagicMock()
sys.modules['discord.ext.tasks'] = MagicMock()

import sentinel

class TestDatabaseInit(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        sentinel.DB_PATH = self.db_path

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_init_db_creates_tables(self):
        sentinel.init_db()
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
        expected = [
            "autorole_config", "automod_events", "league_drivers", "league_races",
            "league_results", "league_teams", "league_seasons", "moderation_actions",
            "reminders", "server_config", "steward_cases", "users", "verification_config",
            "warnings", "welcome_config"
        ]
        for t in expected:
            self.assertIn(t, tables)
        conn.close()

    def test_db_fetch_returns_rows(self):
        sentinel.init_db()
        rows = sentinel.db_fetch("SELECT name FROM sqlite_master WHERE type='table'")
        self.assertIsInstance(rows, list)
        self.assertGreater(len(rows), 0)

    def test_db_execute_insert(self):
        sentinel.init_db()
        last_id = sentinel.db_execute("INSERT INTO users (user_id, username, display_name, joined_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                                       (1, "test", "Test", "2024-01-01", "2024-01-01", "2024-01-01"))
        self.assertGreater(last_id, 0)
        row = sentinel.db_fetch("SELECT * FROM users WHERE user_id = ?", (1,), one=True)
        self.assertEqual(row["username"], "test")

class TestHelpers(unittest.TestCase):
    def test_utc_iso_format(self):
        iso = sentinel.utc_iso()
        self.assertIn("+00:00", iso)

    def test_is_dangerous_role_admin(self):
        role = MagicMock()
        role.permissions.administrator = True
        self.assertTrue(sentinel.is_dangerous_role(role))

    def test_is_dangerous_role_safe(self):
        role = MagicMock()
        role.permissions.administrator = False
        role.permissions.manage_guild = False
        role.permissions.manage_roles = False
        role.permissions.manage_channels = False
        role.permissions.ban_members = False
        role.permissions.kick_members = False
        role.permissions.manage_webhooks = False
        self.assertFalse(sentinel.is_dangerous_role(role))

class TestAutoMod(unittest.TestCase):
    def setUp(self):
        self.am = sentinel.AutoModEngine()
        self.guild_id = 123
        self.user_id = 456

    def test_exempt_role(self):
        member = MagicMock()
        member.guild.id = self.guild_id
        role = MagicMock()
        role.id = 999
        member.roles = [role]
        self.am.exempt_roles[self.guild_id].add(999)
        self.assertTrue(self.am.is_exempt(member))

class TestGuildIsolation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        sentinel.DB_PATH = self.db_path
        sentinel.init_db()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)

    def test_welcome_config_isolated(self):
        sentinel.db_execute("INSERT INTO welcome_config (guild_id, enabled) VALUES (?, ?)", (1, 1))
        sentinel.db_execute("INSERT INTO welcome_config (guild_id, enabled) VALUES (?, ?)", (2, 0))
        row1 = sentinel.db_fetch("SELECT * FROM welcome_config WHERE guild_id = ?", (1,), one=True)
        row2 = sentinel.db_fetch("SELECT * FROM welcome_config WHERE guild_id = ?", (2,), one=True)
        self.assertTrue(row1["enabled"])
        self.assertFalse(row2["enabled"])

    def test_moderation_actions_isolated(self):
        sentinel.db_execute("INSERT INTO moderation_actions (guild_id, action, target_id, moderator_id, reason, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (1, "warn", 100, 200, "test", sentinel.utc_iso()))
        rows1 = sentinel.db_fetch("SELECT * FROM moderation_actions WHERE guild_id = ?", (1,))
        rows2 = sentinel.db_fetch("SELECT * FROM moderation_actions WHERE guild_id = ?", (2,))
        self.assertEqual(len(rows1), 1)
        self.assertEqual(len(rows2), 0)

class TestTokenConfig(unittest.TestCase):
    def test_fallback_token_empty(self):
        self.assertEqual(sentinel.FALLBACK_DISCORD_TOKEN, "")

    def test_env_token_used_when_set(self):
        with patch.dict(os.environ, {"DISCORD_TOKEN": "env_token"}):
            token = os.environ.get("DISCORD_TOKEN") or sentinel.FALLBACK_DISCORD_TOKEN
            self.assertEqual(token, "env_token")

    def test_fallback_used_when_env_empty(self):
        with patch.dict(os.environ, {}, clear=True):
            token = os.environ.get("DISCORD_TOKEN") or sentinel.FALLBACK_DISCORD_TOKEN
            self.assertEqual(token, "")

if __name__ == "__main__":
    unittest.main()
