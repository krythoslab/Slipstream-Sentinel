import json
from pathlib import Path
from typing import Any, Dict, Optional

from src.config import DATA_DIR

CONFIG_FILE = DATA_DIR / "config.json"


def _load() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: Dict[str, Any]) -> None:
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


def get_modlog_channel_id() -> int:
    return int(get("modlog_channel_id", 0) or 0)


def set_modlog_channel_id(channel_id: int) -> None:
    set("modlog_channel_id", channel_id)