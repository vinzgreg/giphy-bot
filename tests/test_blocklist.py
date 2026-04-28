import importlib
import json
from pathlib import Path

import blocklist


def _reload_blocklist(tmp_path: Path):
    """Reset the blocklist module to use a tmp file."""
    blocklist._BLOCKED_FILE = tmp_path / "blocked.json"
    blocklist._blocked = set()


def test_load_empty_when_file_missing(tmp_path):
    _reload_blocklist(tmp_path)
    blocklist.load()
    assert blocklist.is_blocked("anything") is False


def test_load_existing_file(tmp_path):
    _reload_blocklist(tmp_path)
    (tmp_path / "blocked.json").write_text(json.dumps(["abc", "def"]))
    blocklist.load()
    assert blocklist.is_blocked("abc") is True
    assert blocklist.is_blocked("def") is True
    assert blocklist.is_blocked("xyz") is False


def test_block_persists_to_disk(tmp_path):
    _reload_blocklist(tmp_path)
    blocklist.block("gif123")
    assert blocklist.is_blocked("gif123") is True

    saved = json.loads((tmp_path / "blocked.json").read_text())
    assert "gif123" in saved


def test_block_idempotent(tmp_path):
    _reload_blocklist(tmp_path)
    blocklist.block("gif123")
    blocklist.block("gif123")
    saved = json.loads((tmp_path / "blocked.json").read_text())
    assert saved.count("gif123") == 1


def test_load_handles_corrupt_file(tmp_path):
    _reload_blocklist(tmp_path)
    (tmp_path / "blocked.json").write_text("{not valid json")
    blocklist.load()
    assert blocklist.is_blocked("anything") is False
