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
    local_path: Optional[str] = None


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
        # Maps any toot/DM ID in the conversation thread to its session_id.
        # When the bot DMs back, the new ID gets linked here so user replies
        # to the bot's DMs can find the session.
        self._reply_index: dict[str, str] = {}
        self._rate_limits: dict[str, float] = {}

    def get(self, session_id: str) -> Optional[GiphySession]:
        return self._sessions.get(session_id)

    def find_by_reply(self, in_reply_to_id: str) -> Optional[GiphySession]:
        if not in_reply_to_id:
            return None
        # Direct hit: reply was to the original toot
        session = self._sessions.get(in_reply_to_id)
        if session:
            return session
        # Indirect: reply was to one of the bot's DMs in the thread
        sid = self._reply_index.get(in_reply_to_id)
        if sid:
            return self._sessions.get(sid)
        return None

    def link_reply(self, session_id: str, new_toot_id: str) -> None:
        """Register a new bot-sent toot ID as belonging to this session."""
        if not new_toot_id or session_id not in self._sessions:
            return
        self._reply_index[new_toot_id] = session_id

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
        # Clean up reply index entries pointing at this session
        stale = [k for k, v in self._reply_index.items() if v == session_id]
        for k in stale:
            del self._reply_index[k]

    def evict_expired(self) -> None:
        now = time.monotonic()
        ttl = config.session_ttl_seconds
        expired = [sid for sid, s in self._sessions.items()
                   if now - s.last_activity > ttl]
        for sid in expired:
            self.delete(sid)

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
