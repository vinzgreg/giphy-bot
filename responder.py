import logging
from typing import Optional

import requests

from circuit_breaker import CircuitBreaker
from session import GifResult


class Responder:
    """Sends messages via Mastodon. All public-facing posts go through the
    circuit breaker. Admin notifications bypass it (so the admin can always
    be reached, even when the breaker is open).

    All send methods return the new status ID on success, or None on failure
    or when the breaker dropped the message. Callers can use the ID to link
    the new toot to a session for thread tracking.
    """

    def __init__(self, mastodon, breaker: Optional[CircuitBreaker] = None,
                 admin_acct: str = ""):
        self._m = mastodon
        self._breaker = breaker
        self._admin_acct = admin_acct

    def dm(self, to_acct: str, in_reply_to_id: str, text: str) -> Optional[str]:
        return self._guarded_post(
            f"@{to_acct} {text}",
            in_reply_to_id=in_reply_to_id,
            visibility="direct",
        )

    def post_gif(self, to_acct: str, in_reply_to_id: str,
                 gif: GifResult, visibility: str) -> Optional[str]:
        # NOTE: in_reply_to_id is intentionally ignored for the GIF post.
        # Mastodon restricts boost visibility for replies and for posts
        # starting with @mentions to mutual followers of both accounts.
        # Posting as a standalone toot with the mention at the end keeps
        # attribution visible while letting boosts reach normal audiences.
        label = "🏠" if gif.is_local else "🌐"
        text = f"{label} {gif.title}\nvia @{to_acct}"
        if gif.is_local and gif.local_path:
            media_id = self._upload_media_file(gif.local_path, gif.title)
        else:
            media_id = self._upload_media_url(gif.url, gif.title)
        if media_id is None:
            return None
        return self._guarded_post(text, visibility=visibility,
                                   media_ids=[media_id])

    def _upload_media_file(self, path: str, description: str) -> Optional[str]:
        try:
            media = self._m.media_post(path, description=description)
            return str(media["id"])
        except Exception:
            logging.exception("Failed to upload local GIF: %s", path)
            return None

    def _upload_media_url(self, url: str, description: str) -> Optional[str]:
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            mime_type = resp.headers.get("Content-Type", "image/gif").split(";")[0].strip()
            media = self._m.media_post(
                resp.content, mime_type=mime_type, description=description,
            )
            return str(media["id"])
        except Exception:
            logging.exception("Failed to upload remote GIF: %s", url)
            return None

    def error(self, to_acct: str, in_reply_to_id: str, message: str) -> Optional[str]:
        return self.dm(to_acct, in_reply_to_id, message)

    def gif_list(self, to_acct: str, in_reply_to_id: str,
                 keyword: str, gifs: list, offset: int = 0) -> Optional[str]:
        lines = [f"GIFs for \"{keyword}\":"]
        for i, gif in enumerate(gifs, start=offset + 1):
            label = "🏠 (local)" if gif.is_local else "🌐"
            lines.append(f"{i}. {gif.url}  {label} {gif.title}")
        lines.append("")
        lines.append(
            "Reply: 'send N' to post · 'next' for more · 'block' to ban this GIF "
            "· new keyword to search again · 'cancel' to quit"
        )
        return self.dm(to_acct, in_reply_to_id, "\n".join(lines))

    def notify_admin(self, message: str) -> None:
        """Send a DM to the admin. Bypasses the circuit breaker so the admin
        is always reachable. Silently no-ops if no admin is configured."""
        if not self._admin_acct:
            logging.warning("Admin notification suppressed (ADMIN_ACCT not set): %s", message)
            return
        try:
            self._m.status_post(
                f"@{self._admin_acct} [giphy-bot] {message}",
                visibility="direct",
            )
            logging.info("Admin notified: %s", message)
        except Exception:
            logging.exception("Failed to notify admin (%s)", self._admin_acct)

    def _guarded_post(self, text: str, **kwargs) -> Optional[str]:
        if self._breaker is not None and not self._breaker.acquire():
            logging.warning("Circuit breaker open — dropping message: %s",
                            text[:80])
            return None
        try:
            result = self._m.status_post(text, **kwargs)
            if result and "id" in result:
                return str(result["id"])
            return None
        except Exception:
            logging.exception("Failed to post status")
            return None
