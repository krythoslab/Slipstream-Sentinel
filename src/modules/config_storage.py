import json
from pathlib import Path
from typing import Any, Optional

from src.config import DATA_DIR

CONFIG_FILE = DATA_DIR / "config.json"


def _load() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: dict[str, Any]) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get(key: str, default: Any = None) -> Any:
    return _load().get(key, default)


def set(key: str, value: Any) -> None:
    data = _load()
    data[key] = value
    _save(data)


def get_welcome_channel_id() -> int:
    return int(get("welcome_channel_id", 0) or 0)


def set_welcome_channel_id(channel_id: int) -> None:
    set("welcome_channel_id", channel_id)


def get_leave_channel_id() -> int:
    return int(get("leave_channel_id", 0) or 0)


def set_leave_channel_id(channel_id: int) -> None:
    set("leave_channel_id", channel_id)


def get_modlog_channel_id() -> int:
    return int(get("modlog_channel_id", 0) or 0)


def set_modlog_channel_id(channel_id: int) -> None:
    set("modlog_channel_id", channel_id)


def get_announcement_channel_id() -> int:
    return int(get("announcement_channel_id", 0) or 0)


def set_announcement_channel_id(channel_id: int) -> None:
    set("announcement_channel_id", channel_id)


def get_automod_alert_channel_id() -> int:
    return int(get("automod_alert_channel_id", 0) or 0)


def set_automod_alert_channel_id(channel_id: int) -> None:
    set("automod_alert_channel_id", channel_id)


def get_welcome_message() -> str:
    return str(get("welcome_message", "Welcome to {server}, {user}! Please review the rules and introduce yourself."))


def set_welcome_message(message: str) -> None:
    set("welcome_message", message)


def get_leave_message() -> str:
    return str(get("leave_message", "{user} has left {server}. We hope to see you again!"))


def set_leave_message(message: str) -> None:
    set("leave_message", message)


def get_automod_mention_threshold(default: int = 8) -> int:
    return int(get("automod_mention_threshold", default) or default)


def set_automod_mention_threshold(value: int) -> None:
    set("automod_mention_threshold", value)


def get_automod_url_threshold(default: int = 3) -> int:
    return int(get("automod_url_threshold", default) or default)


def set_automod_url_threshold(value: int) -> None:
    set("automod_url_threshold", value)


def get_automod_spam_threshold(default: int = 5) -> int:
    return int(get("automod_spam_threshold", default) or default)


def set_automod_spam_threshold(value: int) -> None:
    set("automod_spam_threshold", value)


def get_automod_spam_window(default: float = 5.0) -> float:
    return float(get("automod_spam_window", default) or default)


def set_automod_spam_window(value: float) -> None:
    set("automod_spam_window", value)


def get_automod_raid_threshold(default: int = 10) -> int:
    return int(get("automod_raid_threshold", default) or default)


def set_automod_raid_threshold(value: int) -> None:
    set("automod_raid_threshold", value)


def get_automod_raid_window(default: float = 60.0) -> float:
    return float(get("automod_raid_window", default) or default)


def set_automod_raid_window(value: float) -> None:
    set("automod_raid_window", value)


def is_staff_member(user_id: int) -> bool:
    return bool(get("staff_ids", {}).get(str(user_id), False))


def add_staff_member(user_id: int) -> None:
    data = _load()
    staff = data.get("staff_ids", {})
    staff[str(user_id)] = True
    data["staff_ids"] = staff
    _save(data)


def remove_staff_member(user_id: int) -> None:
    data = _load()
    staff = data.get("staff_ids", {})
    staff.pop(str(user_id), None)
    data["staff_ids"] = staff
    _save(data)


def get_exempt_channel_ids() -> list[int]:
    return [int(c) for c in get("exempt_channel_ids", [])]


def add_exempt_channel(channel_id: int) -> None:
    data = _load()
    exempt = [int(c) for c in data.get("exempt_channel_ids", [])]
    if channel_id not in exempt:
        exempt.append(channel_id)
    data["exempt_channel_ids"] = exempt
    _save(data)


def remove_exempt_channel(channel_id: int) -> None:
    data = _load()
    exempt = [int(c) for c in data.get("exempt_channel_ids", [])]
    if channel_id in exempt:
        exempt.remove(channel_id)
    data["exempt_channel_ids"] = exempt
    _save(data)


def get_exempt_role_ids() -> list[int]:
    return [int(r) for r in get("exempt_role_ids", [])]


def add_exempt_role(role_id: int) -> None:
    data = _load()
    exempt = [int(r) for r in data.get("exempt_role_ids", [])]
    if role_id not in exempt:
        exempt.append(role_id)
    data["exempt_role_ids"] = exempt
    _save(data)


def remove_exempt_role(role_id: int) -> None:
    data = _load()
    exempt = [int(r) for r in data.get("exempt_role_ids", [])]
    if role_id in exempt:
        exempt.remove(role_id)
    data["exempt_role_ids"] = exempt
    _save(data)