import logging
from typing import Optional

from circuit_breaker import CircuitBreaker
from session import GifResult


class Responder:
    """Sends messages via Mastodon. All public-facing posts go through the
    circuit breaker. Admin notifications bypass it (so the admin can always
    be reached, even when the breaker is open)."""

    def __init__(self, mastodon, breaker: Optional[CircuitBreaker] = None,
                 admin_acct: str = ""):
        self._m = mastodon
        self._breaker = breaker
        self._admin_acct = admin_acct

    def dm(self, to_acct: str, in_reply_to_id: str, text: str) -> None:
        self._guarded_post(
            f"@{to_acct} {text}",
            in_reply_to_id=in_reply_to_id,
            visibility="direct",
        )

    def post_gif(self, to_acct: str, in_reply_to_id: str,
                 gif: GifResult, visibility: str) -> None:
        label = "🏠" if gif.is_local else "🌐"
        text = f"@{to_acct} {label} {gif.title}\n{gif.url}"
        self._guarded_post(text, in_reply_to_id=in_reply_to_id, visibility=visibility)

    def error(self, to_acct: str, in_reply_to_id: str, message: str) -> None:
        self.dm(to_acct, in_reply_to_id, message)

    def gif_list(self, to_acct: str, in_reply_to_id: str,
                 keyword: str, gifs: list, offset: int = 0) -> None:
        lines = [f"GIFs for \"{keyword}\":"]
        for i, gif in enumerate(gifs, start=offset + 1):
            label = "🏠 (local)" if gif.is_local else "🌐"
            lines.append(f"{i}. {gif.url}  {label} {gif.title}")
        lines.append("")
        lines.append(
            "Reply: 'send N' to post · 'next' for more · 'block' to ban this GIF "
            "· new keyword to search again · 'cancel' to quit"
        )
        self.dm(to_acct, in_reply_to_id, "\n".join(lines))

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

    def _guarded_post(self, text: str, **kwargs) -> None:
        if self._breaker is not None and not self._breaker.acquire():
            logging.warning("Circuit breaker open — dropping message: %s",
                            text[:80])
            return
        try:
            self._m.status_post(text, **kwargs)
        except Exception:
            logging.exception("Failed to post status")
