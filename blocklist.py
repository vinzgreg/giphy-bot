import json
import logging
import os
from pathlib import Path

_BLOCKED_FILE = Path("blocked.json")
_blocked: set[str] = set()


def load() -> None:
    global _blocked
    if _BLOCKED_FILE.exists():
        try:
            data = json.loads(_BLOCKED_FILE.read_text())
            _blocked = set(data)
            logging.info("Loaded %d blocked GIF IDs", len(_blocked))
        except Exception:
            logging.warning("Could not load blocked.json, starting empty")
            _blocked = set()
    else:
        _blocked = set()


def is_blocked(gif_id: str) -> bool:
    return gif_id in _blocked


def block(gif_id: str) -> None:
    _blocked.add(gif_id)
    _save()


def _save() -> None:
    tmp = _BLOCKED_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(sorted(_blocked), indent=2))
    tmp.replace(_BLOCKED_FILE)
