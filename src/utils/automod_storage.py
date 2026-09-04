import json
from pathlib import Path
from typing import List


BANNED_WORDS_FILE = Path(__file__).resolve().parent.parent / "data" / "banned_words.json"


def load_banned_words() -> List[str]:
    if not BANNED_WORDS_FILE.exists():
        BANNED_WORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
        BANNED_WORDS_FILE.write_text(json.dumps([]), encoding="utf-8")
        return []
    try:
        data = json.loads(BANNED_WORDS_FILE.read_text(encoding="utf-8"))
        return [w.lower() for w in data if isinstance(w, str)]
    except Exception:
        return []


def save_banned_words(words: List[str]) -> None:
    BANNED_WORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    BANNED_WORDS_FILE.write_text(
        json.dumps(list(set(w.lower() for w in words)), indent=2), encoding="utf-8"
    )
