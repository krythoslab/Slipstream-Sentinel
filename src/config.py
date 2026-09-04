import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
GUILD_ID = os.getenv("GUILD_ID")
WELCOME_CHANNEL_ID = os.getenv("WELCOME_CHANNEL_ID")
MODLOG_CHANNEL_ID = os.getenv("MODLOG_CHANNEL_ID")


def validate() -> None:
    for var in ("DISCORD_TOKEN", "CLIENT_ID", "GUILD_ID"):
        if not os.getenv(var):
            raise RuntimeError(f"Missing required environment variable: {var}")
