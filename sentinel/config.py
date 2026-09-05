import os
from pathlib import Path

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")

CLIENT_ID = 1545480902841339935

DATA_DIR = os.environ.get("DATA_DIR")
if DATA_DIR:
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    DB_PATH = str(Path(DATA_DIR) / "sentinel.db")
else:
    for candidate in [Path.cwd(), Path("/tmp"), Path.home()]:
        try:
            test_path = candidate / "sentinel.db"
            test_path.touch(exist_ok=True)
            DB_PATH = str(test_path)
            break
        except (OSError, PermissionError):
            continue
    else:
        raise RuntimeError("No writable directory found for SQLite database.")

AUTOMOD_DEFAULTS = {
    "spam_threshold": 5,
    "spam_window_seconds": 10,
    "repeat_threshold": 3,
    "repeat_window_seconds": 60,
    "mention_threshold": 5,
    "caps_threshold": 0.7,
    "emoji_threshold": 0.5,
    "invite_action": "warn",
    "url_action": "delete",
    "word_action": "delete",
    "enabled": 1,
}

RATELIMIT_WINDOW = 60
RATELIMIT_MAX_INTERACTIONS = 5
