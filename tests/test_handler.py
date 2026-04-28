"""Tests for GiphyBotListener session linking and rate-limit scoping.

Covers two recent fixes:
1. Per-user rate limit applies only to actual GIF posting (send/shuffle),
   not to interactive commands (search, next, block).
2. Bot DM IDs are linked to the session so the user can keep replying in
   the DM thread without losing the session.
"""
from unittest.mock import patch

from config import config
from handler import GiphyBotListener
from session import GifResult, SessionStore


def _gifs(n=3):
    return [
        GifResult(id=f"g{i}", title=f"t{i}", url=f"u{i}", page_url=f"p{i}")
        for i in range(n)
    ]


class FakeMastodon:
    pass


class RecordingResponder:
    """Returns a unique ID for every send so we can verify link_reply is called."""

    def __init__(self):
        self.calls = []
        self._counter = 0

    def _next_id(self):
        self._counter += 1
        return f"bot-dm-{self._counter}"

    def dm(self, *a, **kw):
        nid = self._next_id()
        self.calls.append(("dm", nid))
        return nid

    def post_gif(self, *a, **kw):
        nid = self._next_id()
        self.calls.append(("post_gif", nid))
        return nid

    def error(self, *a, **kw):
        nid = self._next_id()
        self.calls.append(("error", nid))
        return nid

    def gif_list(self, *a, **kw):
        nid = self._next_id()
        self.calls.append(("gif_list", nid))
        return nid

    def notify_admin(self, *a, **kw):
        pass


def _mention(toot_id, acct, content, in_reply_to=None):
    return {
        "type": "mention",
        "status": {
            "id": toot_id,
            "account": {"id": "999", "acct": acct},
            "content": content,
            "in_reply_to_id": in_reply_to,
        },
    }


def test_new_search_links_dm_to_session():
    store = SessionStore()
    resp = RecordingResponder()
    listener = GiphyBotListener(FakeMastodon(), store, resp)

    with patch("handler._combined_search", return_value=_gifs(3)):
        listener.on_notification(_mention("toot-1", "alice", "puppies"))

    bot_dm_id = next(nid for kind, nid in resp.calls if kind == "gif_list")
    # User replies to the bot's DM, not the original toot
    assert store.find_by_reply(bot_dm_id) is not None


def test_search_does_not_rate_limit():
    store = SessionStore()
    store.record_trigger("alice")  # alice just posted a GIF
    resp = RecordingResponder()
    listener = GiphyBotListener(FakeMastodon(), store, resp)

    with patch("handler._combined_search", return_value=_gifs(3)):
        listener.on_notification(_mention("toot-1", "alice", "kittens"))

    # No rate-limit error: gif_list is sent normally
    kinds = [k for k, _ in resp.calls]
    assert "gif_list" in kinds
    assert "error" not in kinds


def test_send_enforces_rate_limit():
    store = SessionStore()
    resp = RecordingResponder()
    listener = GiphyBotListener(FakeMastodon(), store, resp)

    # Set up a session by hand
    session = store.create("toot-1", "alice", "puppies", _gifs(3), "unlisted")
    store.link_reply(session.session_id, "bot-dm-prev")
    store.record_trigger("alice")  # alice just posted

    listener.on_notification(_mention(
        "toot-2", "alice", "send 1", in_reply_to="bot-dm-prev",
    ))

    # Should get a rate-limit error, not a post_gif
    kinds = [k for k, _ in resp.calls]
    assert "post_gif" not in kinds
    assert "error" in kinds


def test_send_succeeds_when_not_rate_limited():
    store = SessionStore()
    resp = RecordingResponder()
    listener = GiphyBotListener(FakeMastodon(), store, resp)

    session = store.create("toot-1", "alice", "puppies", _gifs(3), "unlisted")
    store.link_reply(session.session_id, "bot-dm-prev")

    listener.on_notification(_mention(
        "toot-2", "alice", "send 2", in_reply_to="bot-dm-prev",
    ))

    kinds = [k for k, _ in resp.calls]
    assert kinds == ["post_gif"]
    # Session was deleted after successful post
    assert store.get(session.session_id) is None


def test_next_in_thread_links_new_dm_to_session():
    store = SessionStore()
    resp = RecordingResponder()
    listener = GiphyBotListener(FakeMastodon(), store, resp)

    session = store.create("toot-1", "alice", "puppies", _gifs(6), "unlisted")
    store.link_reply(session.session_id, "bot-dm-first")

    # User replies "next" to the bot's first DM
    listener.on_notification(_mention(
        "toot-2", "alice", "next", in_reply_to="bot-dm-first",
    ))

    new_dm_id = next(nid for kind, nid in resp.calls if kind == "gif_list")
    # Subsequent reply to the *new* bot DM should still find the session
    assert store.find_by_reply(new_dm_id) is session


def test_shuffle_enforces_rate_limit():
    import giphy as giphy_mod

    store = SessionStore()
    resp = RecordingResponder()
    listener = GiphyBotListener(FakeMastodon(), store, resp)
    store.record_trigger("alice")

    with patch.object(giphy_mod, "random_gif", return_value=_gifs(1)[0]):
        listener.on_notification(_mention("toot-1", "alice", "shuffle"))

    kinds = [k for k, _ in resp.calls]
    assert "post_gif" not in kinds
    assert "error" in kinds
