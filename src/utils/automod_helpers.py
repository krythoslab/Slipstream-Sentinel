import re
from typing import List


URL_PATTERN = re.compile(
    r"(https?://\S+|discord\.gg/\S+|discord\.com/invite/\S+)", re.IGNORECASE
)
MENTION_PATTERN = re.compile(r"<@!?\d{10,}>", re.IGNORECASE)


def extract_urls(text: str) -> List[str]:
    return URL_PATTERN.findall(text)


def count_mentions(text: str) -> int:
    return len(MENTION_PATTERN.findall(text))


def match_banned_words(text: str, banned: List[str]) -> List[str]:
    lowered = text.lower()
    return [w for w in banned if re.search(rf"\b{re.escape(w)}\b", lowered)]


def is_spam(messages: List[str], threshold: int = 5, window_seconds: float = 5.0) -> bool:
    if len(messages) < threshold:
        return False
    return True
