"""Pure-function parsing helpers — no external dependencies, fully testable.

Kept separate from handler.py so unit tests don't pull in mastodon/requests.
"""
import html
import re

_MENTION_SPAN_RE = re.compile(r'<span class="h-card">.*?</span>', re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_AT_RE = re.compile(r"@\s*\S+")  # catches leftover @ fragments after tag stripping
_SEND_RE = re.compile(r"^send(?:\s+(\d+))?$")


def clean_content(text: str) -> str:
    """Strip HTML, mentions, and collapse whitespace from a Mastodon toot."""
    without_mentions = _MENTION_SPAN_RE.sub("", text)
    without_tags = html.unescape(_TAG_RE.sub(" ", without_mentions))
    without_ats = _AT_RE.sub("", without_tags)
    return " ".join(without_ats.split())


def parse_command(text: str) -> tuple[str, str]:
    """Map cleaned content to (command, arg).

    Commands: search, shuffle, next, send, block, cancel, empty.
    """
    clean = " ".join(text.split())
    low = clean.lower()

    if not clean:
        return ("empty", "")
    if low in ("shuffle", "random"):
        return ("shuffle", "")
    if low == "next":
        return ("next", "")
    if low == "cancel":
        return ("cancel", "")
    if low == "block":
        return ("block", "")

    m = _SEND_RE.match(low)
    if m:
        return ("send", m.group(1) or "1")

    return ("search", clean)
