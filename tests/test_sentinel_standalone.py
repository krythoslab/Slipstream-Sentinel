import ast
import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

SENTINEL_FILE = Path(__file__).resolve().parent.parent / "sentinel.py"


class TestSentinelStandalone(unittest.TestCase):
    def _parse(self) -> ast.Module:
        source = SENTINEL_FILE.read_text(encoding="utf-8")
        return ast.parse(source)

    def test_no_src_imports(self) -> None:
        tree = self._parse()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("src"):
                    self.fail(f"Found local src import: {node.module}")
                for alias in node.names:
                    if alias.name.startswith("src"):
                        self.fail(f"Found local src import: {alias.name}")

    def test_has_validate_function(self) -> None:
        tree = self._parse()
        names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        self.assertIn("validate", names)

    def test_has_run_function(self) -> None:
        tree = self._parse()
        names = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertIn("run", names)

    def test_has_bot_class(self) -> None:
        tree = self._parse()
        names = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
        self.assertIn("SlipstreamBot", names)

    def test_has_all_cogs(self) -> None:
        tree = self._parse()
        names = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
        expected = {
            "AdminCog",
            "ModerationCog",
            "AutoModCog",
            "WelcomeCog",
            "InfoCog",
            "ConfigCog",
            "AnnouncementsCog",
            "RolesCog",
            "InfoServerCog",
            "PollsCog",
            "LeagueCog",
            "RaceControlCog",
            "AutomationCog",
        }
        for name in expected:
            self.assertIn(name, names, f"Missing cog class: {name}")

    def test_has_main_block(self) -> None:
        tree = self._parse()
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                if isinstance(node.test, ast.Compare):
                    if (
                        isinstance(node.test.left, ast.Name)
                        and node.test.left.id == "__name__"
                    ):
                        found = True
        self.assertTrue(found, "Missing if __name__ == '__main__' block")

    def test_no_hardcoded_tokens(self) -> None:
        source = SENTINEL_FILE.read_text(encoding="utf-8")
        self.assertNotIn("DISCORD_TOKEN=", source.split("import")[0])
        self.assertNotIn("DISCORD_TOKEN =", source)
        self.assertNotRegex(source, r"DISCORD_TOKEN\s*=\s*['\"][A-Za-z0-9]{20,}['\"]")

    def test_reads_env_vars_from_os_getenv(self) -> None:
        source = SENTINEL_FILE.read_text(encoding="utf-8")
        self.assertIn("os.getenv", source)
        self.assertIn('DISCORD_TOKEN', source)
        self.assertIn('CLIENT_ID', source)
        self.assertIn('GUILD_ID', source)

    def test_has_data_dir_fallback(self) -> None:
        source = SENTINEL_FILE.read_text(encoding="utf-8")
        self.assertIn("_resolve_data_dir", source)
        self.assertIn("DATA_DIR", source)
        self.assertIn("/tmp/slipstream-sentinel", source)

    def test_no_sleep_until_in_remind(self) -> None:
        source = SENTINEL_FILE.read_text(encoding="utf-8")
        self.assertNotIn("sleep_until", source, "remind must not use sleep_until")

    def test_reminders_table_exists(self) -> None:
        source = SENTINEL_FILE.read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS reminders", source)

    def test_reminder_loop_queries_due_reminders(self) -> None:
        source = SENTINEL_FILE.read_text(encoding="utf-8")
        self.assertIn("SELECT id, user_id, channel_id, message FROM reminders WHERE due_at <= ?", source)
        self.assertIn("DELETE FROM reminders WHERE id IN", source)

    def test_creates_sqlite_tables(self) -> None:
        source = SENTINEL_FILE.read_text(encoding="utf-8")
        expected_tables = [
            "mod_actions",
            "warnings",
            "raids",
            "league_drivers",
            "league_teams",
            "league_races",
            "league_results",
            "race_control_cases",
        ]
        for table in expected_tables:
            self.assertIn(table, source, f"Missing SQLite table: {table}")

    def test_cogs_registered_in_setup_hook(self) -> None:
        source = SENTINEL_FILE.read_text(encoding="utf-8")
        expected_cogs = [
            "AdminCog",
            "ModerationCog",
            "AutoModCog",
            "WelcomeCog",
            "InfoCog",
            "ConfigCog",
            "AnnouncementsCog",
            "RolesCog",
            "InfoServerCog",
            "PollsCog",
            "LeagueCog",
            "RaceControlCog",
            "AutomationCog",
        ]
        for cog in expected_cogs:
            self.assertIn(f"await self.add_cog({cog}(self))", source, f"Missing cog registration: {cog}")


if __name__ == "__main__":
    unittest.main()
