import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
CLIENT_ID: str = os.getenv("CLIENT_ID", "1545238354302607450")
GUILD_ID: str = os.getenv("GUILD_ID", "1545179492815741059")
WELCOME_CHANNEL_ID: int = int(os.getenv("WELCOME_CHANNEL_ID", "0") or "0")
MODLOG_CHANNEL_ID: int = int(os.getenv("MODLOG_CHANNEL_ID", "0") or "0")

AUTOMOD_MENTION_THRESHOLD: int = int(os.getenv("AUTOMOD_MENTION_THRESHOLD", "8"))
AUTOMOD_URL_THRESHOLD: int = int(os.getenv("AUTOMOD_URL_THRESHOLD", "3"))
AUTOMOD_SPAM_THRESHOLD: int = int(os.getenv("AUTOMOD_SPAM_THRESHOLD", "5"))
AUTOMOD_SPAM_WINDOW: float = float(os.getenv("AUTOMOD_SPAM_WINDOW", "5.0"))

DATA_DIR: Path = PROJECT_ROOT / "data"
BANNED_WORDS_FILE: Path = DATA_DIR / "banned_words.json"
MODLOG_DB_FILE: Path = DATA_DIR / "modlog.db"


def validate() -> None:
    for var in ("DISCORD_TOKEN", "CLIENT_ID", "GUILD_ID"):
        if not os.getenv(var):
            raise RuntimeError(f"Missing required environment variable: {var}")
