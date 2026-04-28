import time

from session import GifResult, SessionStore


def test_create_and_get_session():
    store = SessionStore()
    s = store.create("toot1", "alice", "cats", [], "unlisted")
    assert store.get("toot1") is s
    assert s.user_acct == "alice"
    assert s.keyword == "cats"


def test_find_by_reply():
    store = SessionStore()
    store.create("toot1", "alice", "cats", [], "unlisted")
    assert store.find_by_reply("toot1") is not None
    assert store.find_by_reply("nonexistent") is None


def test_delete_session():
    store = SessionStore()
    store.create("toot1", "alice", "cats", [], "unlisted")
    store.delete("toot1")
    assert store.get("toot1") is None


def test_evict_expired_removes_old_sessions(monkeypatch):
    store = SessionStore()
    s = store.create("toot1", "alice", "cats", [], "unlisted")
    # Force last_activity into the deep past
    s.last_activity = time.monotonic() - 10_000
    store.evict_expired()
    assert store.get("toot1") is None


def test_evict_keeps_fresh_sessions():
    store = SessionStore()
    store.create("toot1", "alice", "cats", [], "unlisted")
    store.evict_expired()
    assert store.get("toot1") is not None


def test_rate_limit_per_user():
    store = SessionStore()
    assert store.check_rate_limit("alice") is None
    store.record_trigger("alice")
    remaining = store.check_rate_limit("alice")
    assert remaining is not None and remaining > 0


def test_rate_limit_independent_per_user():
    store = SessionStore()
    store.record_trigger("alice")
    assert store.check_rate_limit("bob") is None


def test_gif_result_dataclass():
    g = GifResult(id="abc", title="t", url="u", page_url="p")
    assert g.is_local is False
    g2 = GifResult(id="x", title="t", url="u", page_url="p", is_local=True)
    assert g2.is_local is True
