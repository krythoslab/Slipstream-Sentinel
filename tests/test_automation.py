import ast
import os
import unittest
from pathlib import Path

SOURCE_FILE = Path(__file__).resolve().parent.parent / "src" / "cogs" / "automation.py"


class TestAutomationRemindBugFix(unittest.TestCase):
    def test_no_sleep_until_in_remind(self) -> None:
        source = SOURCE_FILE.read_text(encoding="utf-8")
        self.assertNotIn("sleep_until", source, "remind must not use sleep_until")

    def test_remind_stores_in_sqlite(self) -> None:
        source = SOURCE_FILE.read_text(encoding="utf-8")
        self.assertIn("INSERT INTO reminders", source)
        self.assertIn("due_at", source)
        self.assertIn("timedelta(seconds=seconds)", source)

    def test_reminder_loop_queries_due_reminders(self) -> None:
        source = SOURCE_FILE.read_text(encoding="utf-8")
        self.assertIn("SELECT id, user_id, channel_id, message FROM reminders WHERE due_at <= ?", source)
        self.assertIn("DELETE FROM reminders WHERE id IN", source)

    def test_remind_validates_duration(self) -> None:
        source = SOURCE_FILE.read_text(encoding="utf-8")
        self.assertIn("seconds < 1", source)
        self.assertIn("seconds > 86400", source)

    def test_reminder_loop_runs_every_minute(self) -> None:
        source = SOURCE_FILE.read_text(encoding="utf-8")
        self.assertIn("@tasks.loop(minutes=1)", source)


if __name__ == "__main__":
    unittest.main()
