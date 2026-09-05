import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from discord.interactions import Interaction
from discord.member import Member
from discord.user import User
from discord.guild import Guild
from discord.role import Role
from discord.channel import TextChannel
from discord.abc import Snowflake

from sentinel.database import Database
from sentinel.utils import utcnow_iso, has_perm, hierarchy_ok, is_dangerous_role, safe_send, parse_duration
from sentinel.errors import SlipstreamError, error_response
from sentinel.embeds import info_embed, success_embed, error_embed


class TestDatabaseInit(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.db = Database(":memory:")

    def tearDown(self):
        self.loop.close()

    def test_init_db_creates_tables(self):
        async def run():
            await self.db.connect()
            from sentinel.database import init_db
            await init_db(self.db)
            tables = await self.db.fetch("SELECT name FROM sqlite_master WHERE type='table'")
            names = {r["name"] for r in tables}
            self.assertIn("warnings", names)
            self.assertIn("automod_config", names)
            self.assertIn("automod_whitelist", names)
            self.assertIn("poll_votes", names)
            await self.db.close()
        self.loop.run_until_complete(run())


class TestHelpers(unittest.TestCase):
    def test_utcnow_iso(self):
        val = utcnow_iso()
        self.assertIsInstance(val, str)
        self.assertIn("T", val)

    def test_is_dangerous_role(self):
        role = MagicMock(spec=Role)
        role.permissions.administrator = True
        self.assertTrue(is_dangerous_role(role))

    def test_parse_duration(self):
        self.assertEqual(parse_duration("30m"), 1800)
        self.assertEqual(parse_duration("2h"), 7200)
        self.assertEqual(parse_duration("1d"), 86400)


class TestAutoMod(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_exempt_role_logic(self):
        member = MagicMock(spec=Member)
        member.roles = []
        cog = MagicMock()
        cog._whitelist_cache = {123: {999}}
        member.id = 999
        member.guild.id = 123
        # We test via the is_dangerous_role utility, not the full engine
        role = MagicMock(spec=Role)
        role.permissions.administrator = False
        role.permissions.manage_guild = False
        self.assertFalse(is_dangerous_role(role))


class TestGuildIsolation(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.db = Database(":memory:")

    def tearDown(self):
        self.loop.close()

    def test_welcome_config_isolated(self):
        async def run():
            await self.db.connect()
            from sentinel.database import init_db
            await init_db(self.db)
            await self.db.execute(
                "INSERT INTO welcome_config (guild_id, enabled, channel_id, message) VALUES (?, ?, ?, ?)",
                (1, 1, 100, "welcome")
            )
            await self.db.execute(
                "INSERT INTO welcome_config (guild_id, enabled, channel_id, message) VALUES (?, ?, ?, ?)",
                (2, 1, 200, "welcome2")
            )
            rows = await self.db.fetch("SELECT * FROM welcome_config WHERE guild_id = ?", (1,))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["message"], "welcome")
            await self.db.close()
        self.loop.run_until_complete(run())


class TestTokenConfig(unittest.TestCase):
    def test_missing_token_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(RuntimeError):
                from sentinel import config
                import importlib
                importlib.reload(config)


if __name__ == "__main__":
    unittest.main()
