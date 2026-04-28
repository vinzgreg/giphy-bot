import logging

import blocklist
import giphy
import local_gifs
from config import config
from parser import clean_content, parse_command
from responder import Responder
from session import GiphySession, SessionStore

try:
    from mastodon import StreamListener
except ImportError:
    class StreamListener:
        pass


def _combined_search(keyword: str) -> list:
    local = local_gifs.search(keyword)
    remote = []
    try:
        remote = giphy.search_gifs(keyword)
    except giphy.GiphyError:
        pass
    return local + [r for r in remote if r not in local]


class GiphyBotListener(StreamListener):
    def __init__(self, mastodon, store: SessionStore, responder: Responder):
        self._m = mastodon
        self._store = store
        self._resp = responder

    def on_notification(self, notification):
        ntype = notification.get("type")
        logging.debug("Notification received: type=%s", ntype)
        self._store.evict_expired()

        if ntype == "follow":
            self._handle_follow(notification)
            return

        if ntype != "mention":
            return

        status = notification["status"]
        if str(status["account"]["id"]) == str(config.bot_account_id):
            logging.debug("Ignoring self-mention")
            return
        logging.info("Mention from @%s: %s", status["account"]["acct"],
                     clean_content(status.get("content", "")))
        try:
            self._dispatch(status)
        except Exception:
            logging.exception("Error handling mention from @%s",
                              status["account"]["acct"])

    def _handle_follow(self, notification: dict) -> None:
        if not config.auto_follow_back:
            return
        account = notification.get("account") or {}
        account_id = account.get("id")
        acct = account.get("acct", "?")
        if not account_id:
            logging.warning("Follow notification missing account id")
            return
        try:
            self._m.account_follow(account_id)
            logging.info("Followed back @%s (id=%s)", acct, account_id)
        except Exception:
            logging.exception("Failed to follow back @%s", acct)

    def on_abort(self, err):
        logging.error("Stream aborted: %s", err)

    def on_error(self, err):
        logging.error("Stream error: %s", err)

    def _dispatch(self, status: dict) -> None:
        acct = status["account"]["acct"]
        toot_id = str(status["id"])
        in_reply_to = str(status.get("in_reply_to_id") or "")
        text = clean_content(status.get("content", ""))
        cmd, arg = parse_command(text)

        session = self._store.find_by_reply(in_reply_to) if in_reply_to else None

        if session:
            self._store.touch(session)
            self._handle_session_cmd(session, toot_id, acct, cmd, arg)
        elif cmd == "search":
            self._new_search(toot_id, acct, arg)
        elif cmd == "shuffle":
            self._shuffle(toot_id, acct)
        elif cmd == "empty":
            self._resp.error(acct, toot_id, "Mention me with a keyword to search for a GIF, or 'shuffle' for a random one.")
        elif cmd in ("next", "send", "block", "cancel"):
            self._resp.error(acct, toot_id, "No active GIF session. Mention me with a keyword to start one.")
        else:
            pass

    def _new_search(self, toot_id: str, acct: str, keyword: str) -> None:
        wait = self._store.check_rate_limit(acct)
        if wait:
            self._resp.error(acct, toot_id, f"Please wait {wait}s before requesting another GIF.")
            return
        results = _combined_search(keyword)
        if not results:
            self._resp.error(acct, toot_id, f"No GIFs found for \"{keyword}\". Try a different keyword?")
            return
        self._store.record_trigger(acct)
        session = self._store.create(toot_id, acct, keyword, results, config.bot_visibility)
        self._resp.gif_list(acct, toot_id, keyword, results[:config.giphy_result_count])

    def _shuffle(self, toot_id: str, acct: str) -> None:
        try:
            gif = giphy.random_gif()
        except giphy.GiphyError:
            self._resp.error(acct, toot_id, "Giphy is unavailable right now, sorry.")
            return
        if not gif:
            self._resp.error(acct, toot_id, "Couldn't fetch a random GIF right now.")
            return
        self._resp.post_gif(acct, toot_id, gif, config.bot_visibility)

    def _handle_session_cmd(self, session: GiphySession, toot_id: str,
                             acct: str, cmd: str, arg: str) -> None:
        if cmd == "cancel":
            self._store.delete(session.session_id)
            self._resp.dm(acct, toot_id, "Cancelled. Mention me with a keyword to start fresh.")

        elif cmd == "send":
            idx = int(arg) - 1
            if idx < 0 or idx >= len(session.results):
                self._resp.error(acct, toot_id, f"No GIF #{idx + 1} in this list.")
                return
            gif = session.results[idx]
            self._resp.post_gif(acct, session.session_id, gif, session.visibility)
            self._store.delete(session.session_id)

        elif cmd == "block":
            current = session.results[session.result_index] if session.results else None
            if not current:
                self._resp.error(acct, toot_id, "Nothing to block.")
                return
            if not current.is_local:
                blocklist.block(current.id)
            session.results = [r for r in session.results if r.id != current.id]
            session.result_index = 0
            if not session.results:
                more = _combined_search(session.keyword)
                session.results = [r for r in more if r.id != current.id]
            if session.results:
                self._resp.gif_list(
                    acct, toot_id, session.keyword,
                    session.results[:config.giphy_result_count],
                )
                self._resp.dm(acct, toot_id, f"Blocked {'(local GIFs can only be deleted from disk)' if current.is_local else ''}. Here are your options:")
            else:
                self._resp.error(acct, toot_id, "Blocked. No more GIFs found for this keyword.")
                self._store.delete(session.session_id)

        elif cmd == "next":
            session.result_index += config.giphy_result_count
            page_results = session.results[session.result_index:
                                           session.result_index + config.giphy_result_count]
            if not page_results:
                try:
                    more = giphy.search_gifs(session.keyword, offset=len(session.results))
                except giphy.GiphyError:
                    more = []
                session.results.extend(more)
                page_results = session.results[session.result_index:
                                               session.result_index + config.giphy_result_count]
            if not page_results:
                self._resp.error(acct, toot_id, "No more GIFs. Try a new keyword?")
                session.result_index = max(0, session.result_index - config.giphy_result_count)
            else:
                self._resp.gif_list(acct, toot_id, session.keyword,
                                    page_results, offset=session.result_index)

        elif cmd == "search":
            keyword = arg
            results = _combined_search(keyword)
            if not results:
                self._resp.error(acct, toot_id, f"No GIFs found for \"{keyword}\". Try another?")
                return
            session.keyword = keyword
            session.results = results
            session.result_index = 0
            self._resp.gif_list(acct, toot_id, keyword, results[:config.giphy_result_count])

        else:
            self._resp.error(acct, toot_id,
                             "Unknown command. Reply: 'send N' · 'next' · 'block' · 'cancel' · or a new keyword.")
