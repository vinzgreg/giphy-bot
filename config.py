import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise ValueError(f"Missing required environment variable: {name}")
    return val


@dataclass(frozen=True)
class Config:
    mastodon_access_token: str
    mastodon_client_id: str
    mastodon_client_secret: str
    mastodon_api_base_url: str
    bot_account_id: str

    giphy_api_key: str
    giphy_result_count: int
    giphy_rating: str

    session_ttl_seconds: int
    rate_limit_per_user_seconds: int
    bot_visibility: str

    local_gifs_dir: str
    local_gif_base_url: str
    fuzzy_match_threshold: int


config = Config(
    mastodon_access_token=_require("MASTODON_ACCESS_TOKEN"),
    mastodon_client_id=_require("MASTODON_CLIENT_ID"),
    mastodon_client_secret=_require("MASTODON_CLIENT_SECRET"),
    mastodon_api_base_url=_require("MASTODON_API_BASE_URL"),
    bot_account_id=_require("BOT_ACCOUNT_ID"),
    giphy_api_key=_require("GIPHY_API_KEY"),
    giphy_result_count=int(os.getenv("GIPHY_RESULT_COUNT", "3")),
    giphy_rating=os.getenv("GIPHY_RATING", "g"),
    session_ttl_seconds=int(os.getenv("SESSION_TTL_SECONDS", "600")),
    rate_limit_per_user_seconds=int(os.getenv("RATE_LIMIT_PER_USER_SECONDS", "30")),
    bot_visibility=os.getenv("BOT_VISIBILITY", "unlisted"),
    local_gifs_dir=os.getenv("LOCAL_GIFS_DIR", "./local_gifs"),
    local_gif_base_url=os.getenv("LOCAL_GIF_BASE_URL", ""),
    fuzzy_match_threshold=int(os.getenv("FUZZY_MATCH_THRESHOLD", "65")),
)
