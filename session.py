import time
from dataclasses import dataclass, field
from typing import Optional

from config import config


@dataclass
class GifResult:
    id: str
    title: str
    url: str
    page_url: str
    is_local: bool = False


@dataclass
class GiphySession:
    session_id: str
    user_acct: str
    keyword: str
    results: list
    result_index: int
    created_at: float
    last_activity: float
    visibility: str


class SessionStore:
    def __init__(self):
        self._sessions: dict[str, GiphySession] = {}
        self._rate_limits: dict[str, float] = {}

    def get(self, session_id: str) -> Optional[GiphySession]:
        return self._sessions.get(session_id)

    def find_by_reply(self, in_reply_to_id: str) -> Optional[GiphySession]:
        return self._sessions.get(in_reply_to_id)

    def create(self, session_id: str, user_acct: str, keyword: str,
               results: list, visibility: str) -> GiphySession:
        now = time.monotonic()
        session = GiphySession(
            session_id=session_id,
            user_acct=user_acct,
            keyword=keyword,
            results=results,
            result_index=0,
            created_at=now,
            last_activity=now,
            visibility=visibility,
        )
        self._sessions[session_id] = session
        return session

    def touch(self, session: GiphySession) -> None:
        session.last_activity = time.monotonic()

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def evict_expired(self) -> None:
        now = time.monotonic()
        ttl = config.session_ttl_seconds
        expired = [sid for sid, s in self._sessions.items()
                   if now - s.last_activity > ttl]
        for sid in expired:
            del self._sessions[sid]

    def check_rate_limit(self, user_acct: str) -> Optional[int]:
        """Return seconds remaining if rate-limited, else None."""
        last = self._rate_limits.get(user_acct)
        if last is None:
            return None
        elapsed = time.monotonic() - last
        remaining = config.rate_limit_per_user_seconds - elapsed
        return int(remaining) + 1 if remaining > 0 else None

    def record_trigger(self, user_acct: str) -> None:
        self._rate_limits[user_acct] = time.monotonic()
