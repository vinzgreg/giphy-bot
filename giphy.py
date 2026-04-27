import logging

import requests

import blocklist
from config import config
from session import GifResult

_SESSION = requests.Session()
_BASE = "https://api.giphy.com/v1/gifs"


class GiphyError(Exception):
    pass


def _normalize(data: dict) -> GifResult:
    url = (
        data.get("images", {})
        .get("downsized_medium", {})
        .get("url", "")
        or data.get("images", {}).get("original", {}).get("url", "")
    )
    return GifResult(
        id=data["id"],
        title=data.get("title", ""),
        url=url,
        page_url=data.get("url", ""),
    )


def _filter(results: list[GifResult]) -> list[GifResult]:
    return [r for r in results if not blocklist.is_blocked(r.id)]


def search_gifs(keyword: str, offset: int = 0) -> list[GifResult]:
    keyword = keyword[:50]
    try:
        resp = _SESSION.get(
            f"{_BASE}/search",
            params={
                "api_key": config.giphy_api_key,
                "q": keyword,
                "limit": config.giphy_result_count * 3,
                "offset": offset,
                "rating": config.giphy_rating,
                "lang": "en",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data:
            return []
        results = [_normalize(d) for d in data]
        return _filter(results)[: config.giphy_result_count]
    except requests.RequestException as e:
        logging.error("Giphy search error: %s", e)
        raise GiphyError("Giphy unavailable") from e


def random_gif(tag: str | None = None) -> GifResult | None:
    params = {"api_key": config.giphy_api_key, "rating": config.giphy_rating}
    if tag:
        params["tag"] = tag[:50]
    try:
        resp = _SESSION.get(f"{_BASE}/random", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data")
        if not data:
            return None
        result = _normalize(data)
        if blocklist.is_blocked(result.id):
            return None
        return result
    except requests.RequestException as e:
        logging.error("Giphy random error: %s", e)
        raise GiphyError("Giphy unavailable") from e
