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

    logging.info("Starting Mastodon Giphy Bot...")
    handle = mastodon.stream_user(
        listener,
        run_async=True,
        reconnect_async=True,
        reconnect_async_wait_sec=10,
    )

    def _shutdown(sig, frame):
        logging.info("Shutting down...")
        handle.close()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logging.info("Bot running. Listening for /giphy mentions...")
    while handle.is_alive():
        time.sleep(5)


if __name__ == "__main__":
    main()
