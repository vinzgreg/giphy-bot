from config import config
from handler import GiphyBotListener
from session import SessionStore


class FakeMastodon:
    def __init__(self):
        self.followed = []

    def account_follow(self, account_id):
        self.followed.append(account_id)


class FakeResponder:
    def notify_admin(self, msg): pass
    def dm(self, *a, **kw): pass
    def post_gif(self, *a, **kw): pass
    def error(self, *a, **kw): pass
    def gif_list(self, *a, **kw): pass


def _listener_with_fakes():
    fm = FakeMastodon()
    fr = FakeResponder()
    listener = GiphyBotListener(fm, SessionStore(), fr)
    return listener, fm


def _follow_notification(account_id="42", acct="newuser"):
    return {
        "type": "follow",
        "account": {"id": account_id, "acct": acct},
    }


def test_follow_back_when_enabled():
    object.__setattr__(config, "auto_follow_back", True)
    listener, fm = _listener_with_fakes()
    listener.on_notification(_follow_notification("42"))
    assert fm.followed == ["42"]


def test_no_follow_back_when_disabled():
    object.__setattr__(config, "auto_follow_back", False)
    listener, fm = _listener_with_fakes()
    listener.on_notification(_follow_notification("42"))
    assert fm.followed == []
    object.__setattr__(config, "auto_follow_back", True)  # reset


def test_follow_back_handles_api_error():
    class BoomMastodon:
        def account_follow(self, _):
            raise RuntimeError("api down")

    object.__setattr__(config, "auto_follow_back", True)
    listener = GiphyBotListener(BoomMastodon(), SessionStore(), FakeResponder())
    # Must not raise
    listener.on_notification(_follow_notification("42"))


def test_follow_back_skips_when_account_id_missing():
    object.__setattr__(config, "auto_follow_back", True)
    listener, fm = _listener_with_fakes()
    listener.on_notification({"type": "follow", "account": {"acct": "x"}})
    assert fm.followed == []


def test_non_follow_notification_does_not_trigger():
    object.__setattr__(config, "auto_follow_back", True)
    listener, fm = _listener_with_fakes()
    listener.on_notification({"type": "favourite", "account": {"id": "1"}})
    assert fm.followed == []
