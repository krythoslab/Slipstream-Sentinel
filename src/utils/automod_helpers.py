import re
import time
from typing import List, Dict, Tuple


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
    if window_seconds <= 0:
        return len(messages) >= threshold
    return (messages[-1][0] - messages[0][0]) <= window_seconds


class SpamTracker:
    def __init__(self) -> None:
        self._user_messages: Dict[int, List[Tuple[float, str]]] = {}

    def record(self, user_id: int, content: str) -> None:
        now = time.monotonic()
        history = self._user_messages.setdefault(user_id, [])
        history.append((now, content))
        cutoff = now - 60.0
        self._user_messages[user_id] = [(t, c) for t, c in history if t > cutoff]

    def check(
        self, user_id: int, threshold: int, window_seconds: float
    ) -> Tuple[bool, List[Tuple[float, str]]]:
        history = self._user_messages.get(user_id, [])
        if not history:
            return False, []
        recent = [(t, c) for t, c in history if (history[-1][0] - t) <= window_seconds]
        return is_spam(recent, threshold=threshold, window_seconds=window_seconds), recent
