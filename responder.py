import logging
import time
from typing import Optional

import requests

from circuit_breaker import CircuitBreaker
from session import GifResult

_MEDIA_PROCESSING_TIMEOUT_S = 30
_MEDIA_PROCESSING_POLL_S = 1.0
_MASTODON_MAX_ATTACHMENTS = 4


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
            return self._wait_for_media(media)
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
            return self._wait_for_media(media)
        except Exception:
            logging.exception("Failed to upload remote GIF: %s", url)
            return None

    def _wait_for_media(self, media: dict) -> Optional[str]:
        """Mastodon processes uploaded media asynchronously. Poll until the
        media reports a URL (processing complete) or we hit the timeout."""
        media_id = str(media["id"])
        if media.get("url"):
            return media_id
        deadline = time.monotonic() + _MEDIA_PROCESSING_TIMEOUT_S
        while time.monotonic() < deadline:
            time.sleep(_MEDIA_PROCESSING_POLL_S)
            try:
                current = self._m.media(media_id)
            except Exception:
                logging.exception("Failed to poll media %s", media_id)
                return None
            if current.get("url"):
                return media_id
        logging.error("Media %s did not finish processing within %ds",
                      media_id, _MEDIA_PROCESSING_TIMEOUT_S)
        return None

    def error(self, to_acct: str, in_reply_to_id: str, message: str) -> Optional[str]:
        return self.dm(to_acct, in_reply_to_id, message)

    def gif_list(self, to_acct: str, in_reply_to_id: str,
                 keyword: str, gifs: list, offset: int = 0) -> Optional[str]:
        # Local GIFs have no public URL, so attach them as media in the DM
        # itself (Mastodon allows up to 4 attachments) so the user can preview
        # what they're picking. Remote Giphy GIFs keep a clickable URL.
        lines = [f"GIFs for \"{keyword}\":"]
        media_ids: list[str] = []
        for i, gif in enumerate(gifs, start=offset + 1):
            label = "🏠 (local)" if gif.is_local else "🌐"
            attached = False
            if (gif.is_local and gif.local_path
                    and len(media_ids) < _MASTODON_MAX_ATTACHMENTS):
                mid = self._upload_media_file(gif.local_path, gif.title)
                if mid:
                    media_ids.append(mid)
                    attached = True
            if attached:
                lines.append(f"{i}. {label} {gif.title}")
            elif gif.is_local:
                lines.append(f"{i}. {label} {gif.title} (preview unavailable)")
            else:
                lines.append(f"{i}. {gif.url}  {label} {gif.title}")
        lines.append("")
        lines.append(
            "Reply: 'send N' to post · 'next' for more · 'block' to ban this GIF "
            "· new keyword to search again · 'cancel' to quit"
        )
        text = f"@{to_acct} " + "\n".join(lines)
        kwargs: dict = {"in_reply_to_id": in_reply_to_id, "visibility": "direct"}
        if media_ids:
            kwargs["media_ids"] = media_ids
        return self._guarded_post(text, **kwargs)

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
