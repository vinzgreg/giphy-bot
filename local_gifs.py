import logging
import random
from pathlib import Path

from thefuzz import process as fuzz_process

from config import config
from session import GifResult


_INDEX: list[tuple[str, Path]] = []


def _stem_to_keywords(stem: str) -> str:
    return stem.replace("-", " ").replace("_", " ").lower()


def reload() -> None:
    global _INDEX
    folder = Path(config.local_gifs_dir)
    if not folder.exists():
        folder.mkdir(parents=True, exist_ok=True)
    _INDEX = [
        (_stem_to_keywords(p.stem), p)
        for p in sorted(folder.iterdir())
        if p.suffix.lower() in {".gif", ".webp", ".mp4"}
    ]
    logging.info("Indexed %d local GIFs", len(_INDEX))


def search(keyword: str) -> list[GifResult]:
    if not _INDEX:
        return []
    stems = [stem for stem, _ in _INDEX]
    matches = fuzz_process.extractBests(
        keyword.lower(),
        stems,
        score_cutoff=config.fuzzy_match_threshold,
        limit=config.giphy_result_count,
    )
    results = []
    for matched_stem, _score in matches:
        for stem, path in _INDEX:
            if stem == matched_stem:
                results.append(_to_gif_result(path))
                break
    return results


def random_gif() -> "GifResult | None":
    if not _INDEX:
        return None
    _, path = random.choice(_INDEX)
    return _to_gif_result(path)


def _to_gif_result(path: Path) -> GifResult:
    base_url = config.local_gif_base_url.rstrip("/")
    if base_url:
        url = f"{base_url}/{path.name}"
    else:
        url = path.resolve().as_uri()
    return GifResult(
        id=f"local:{path.stem}",
        title=_stem_to_keywords(path.stem).title(),
        url=url,
        page_url=url,
        is_local=True,
        local_path=str(path.resolve()),
    )
