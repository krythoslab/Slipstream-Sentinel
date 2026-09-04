import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
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


def _resolve_data_dir() -> Path:
    env_dir = os.getenv("DATA_DIR")
    if env_dir:
        return Path(env_dir)
    project_data = PROJECT_ROOT / "data"
    try:
        project_data.mkdir(parents=True, exist_ok=True)
        test_file = project_data / ".write_test"
        test_file.write_text("test", encoding="utf-8")
        test_file.unlink()
        return project_data
    except OSError:
        return Path("/tmp/slipstream-sentinel")


DATA_DIR: Path = _resolve_data_dir()
BANNED_WORDS_FILE: Path = DATA_DIR / "banned_words.json"
MODLOG_DB_FILE: Path = DATA_DIR / "modlog.db"


def validate() -> None:
    for var in ("DISCORD_TOKEN", "CLIENT_ID", "GUILD_ID"):
        if not os.getenv(var):
            raise RuntimeError(f"Missing required environment variable: {var}")