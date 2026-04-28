import os
from pathlib import Path

import local_gifs
from config import config


def _setup_dir(tmp_path: Path) -> None:
    """Point local_gifs module at a tmp directory and reload."""
    object.__setattr__(config, "local_gifs_dir", str(tmp_path))
    object.__setattr__(config, "local_gif_base_url", "")
    local_gifs.reload()


def test_search_empty_when_no_files(tmp_path):
    _setup_dir(tmp_path)
    assert local_gifs.search("anything") == []


def test_search_finds_exact_filename_match(tmp_path):
    _setup_dir(tmp_path)
    (tmp_path / "happy-dog.gif").write_bytes(b"x")
    local_gifs.reload()
    results = local_gifs.search("happy dog")
    assert len(results) >= 1
    assert results[0].is_local is True


def test_search_fuzzy_matches_partial(tmp_path):
    _setup_dir(tmp_path)
    (tmp_path / "excited-puppy-jumping.gif").write_bytes(b"x")
    local_gifs.reload()
    results = local_gifs.search("excited puppy")
    assert len(results) >= 1


def test_search_ignores_non_gif_files(tmp_path):
    _setup_dir(tmp_path)
    (tmp_path / "readme.txt").write_text("not a gif")
    local_gifs.reload()
    assert local_gifs.search("readme") == []


def test_search_below_threshold_returns_nothing(tmp_path):
    _setup_dir(tmp_path)
    (tmp_path / "totally-different-words.gif").write_bytes(b"x")
    local_gifs.reload()
    # Very different keyword should not match
    assert local_gifs.search("xyzabc") == []
