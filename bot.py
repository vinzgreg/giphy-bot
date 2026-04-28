import logging
import signal
import time

from mastodon import Mastodon

import blocklist
import local_gifs
from circuit_breaker import CircuitBreaker
from config import config
from handler import GiphyBotListener
from responder import Responder
from session import SessionStore


def _configure_logging() -> None:
    level = getattr(logging, config.log_level, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )


def _build_breaker(responder_holder: dict) -> CircuitBreaker:
    """Builds the circuit breaker. responder_holder is a one-element dict
    that will be populated with the Responder instance after construction —
    this resolves the chicken-and-egg between breaker callbacks and responder.
    """
    cooldown_min = config.cooldown_seconds // 60
    open_msg = (
        f"⚠️ Rate limit hit ({config.max_messages_per_minute} msgs/min). "
        f"Pausing for {cooldown_min} min(s)."
    )
    close_msg = "✅ Cool-down complete. Bot resuming normal operation."

    def on_open():
        responder = responder_holder.get("r")
        if responder:
            responder.notify_admin(open_msg)

    def on_close():
        responder = responder_holder.get("r")
        if responder:
            responder.notify_admin(close_msg)

    return CircuitBreaker(
        max_per_minute=config.max_messages_per_minute,
        cooldown_seconds=config.cooldown_seconds,
        on_open=on_open,
        on_close=on_close,
    )


def main():
    _configure_logging()
    log = logging.getLogger("bot")

    blocklist.load()
    local_gifs.reload()

    mastodon = Mastodon(
        client_id=config.mastodon_client_id,
        client_secret=config.mastodon_client_secret,
        access_token=config.mastodon_access_token,
        api_base_url=config.mastodon_api_base_url,
    )

    # Verify credentials at startup — fail fast if misconfigured
    try:
        me = mastodon.account_verify_credentials()
        log.info("Logged in as @%s (id=%s)", me["acct"], me["id"])
    except Exception:
        log.exception("Failed to verify credentials — check token and base URL")
        return

    responder_holder: dict = {}
    breaker = _build_breaker(responder_holder)
    responder = Responder(mastodon, breaker=breaker, admin_acct=config.admin_acct)
    responder_holder["r"] = responder

    if not config.admin_acct:
        log.warning("ADMIN_ACCT is not set — circuit breaker events will be logged only")

    store = SessionStore()
    listener = GiphyBotListener(mastodon, store, responder)

    # Initialize since_id from the most recent notification — avoids replaying
    # the entire notification history on first run
    try:
        recent = mastodon.notifications(limit=1)
        since_id = recent[0]["id"] if recent else None
        log.info("Starting from notification id=%s", since_id)
    except Exception:
        log.exception("Could not fetch initial notifications")
        since_id = None

    def _shutdown(sig, frame):
        log.info("Shutting down...")
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    log.info("Bot running. Polling every %ds. Rate limit: %d msgs/min, cool-down: %ds.",
             config.poll_interval_seconds,
             config.max_messages_per_minute,
             config.cooldown_seconds)

    while True:
        time.sleep(config.poll_interval_seconds)
        try:
            kwargs = {"limit": 20}
            if since_id:
                kwargs["since_id"] = since_id
            new_notifications = mastodon.notifications(**kwargs)
            if new_notifications:
                since_id = new_notifications[0]["id"]
                log.debug("Polling: %d new notification(s)", len(new_notifications))
                for notification in reversed(new_notifications):
                    try:
                        listener.on_notification(notification)
                    except Exception:
                        log.exception("Error processing notification")
        except Exception:
            log.exception("Polling loop error — will retry next cycle")


if __name__ == "__main__":
    main()
