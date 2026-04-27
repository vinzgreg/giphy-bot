import logging
import signal
import time

from mastodon import Mastodon

import blocklist
import local_gifs
from config import config
from handler import GiphyBotListener
from responder import Responder
from session import SessionStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def main():
    blocklist.load()
    local_gifs.reload()

    mastodon = Mastodon(
        client_id=config.mastodon_client_id,
        client_secret=config.mastodon_client_secret,
        access_token=config.mastodon_access_token,
        api_base_url=config.mastodon_api_base_url,
    )

    store = SessionStore()
    responder = Responder(mastodon)
    listener = GiphyBotListener(mastodon, store, responder)

    # Verify credentials and check notification access
    try:
        me = mastodon.account_verify_credentials()
        logging.info("Logged in as @%s (id=%s)", me["acct"], me["id"])
    except Exception as e:
        logging.error("Failed to verify credentials: %s", e)
        return

    try:
        notifications = mastodon.notifications(limit=5)
        logging.info("Recent notifications count: %d", len(notifications))
        for n in notifications:
            logging.info("  - type=%s from=%s", n["type"],
                         n.get("account", {}).get("acct", "?"))
    except Exception as e:
        logging.error("Failed to fetch notifications (check token scopes): %s", e)

    # Start from the most recent notification so we don't replay old ones
    try:
        recent = mastodon.notifications(limit=1)
        since_id = recent[0]["id"] if recent else None
    except Exception:
        since_id = None

    def _shutdown(sig, frame):
        logging.info("Shutting down...")
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logging.info("Bot running. Polling for mentions every 10 seconds...")
    while True:
        time.sleep(10)
        try:
            kwargs = {"limit": 20}
            if since_id:
                kwargs["since_id"] = since_id
            new_notifications = mastodon.notifications(**kwargs)
            if new_notifications:
                since_id = new_notifications[0]["id"]
                for notification in reversed(new_notifications):
                    listener.on_notification(notification)
        except Exception as e:
            logging.error("Polling error: %s", e)


if __name__ == "__main__":
    main()
