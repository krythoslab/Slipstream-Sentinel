import asyncio
import sys
from pathlib import Path

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).parent))

from sentinel.config import DB_PATH, DISCORD_TOKEN
from sentinel.database import Database
from sentinel.bot import SentinelBot


def main():
    db = Database(DB_PATH)
    bot = SentinelBot(db)
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
