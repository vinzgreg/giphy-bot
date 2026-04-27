import logging

from session import GifResult


class Responder:
    def __init__(self, mastodon):
        self._m = mastodon

    def dm(self, to_acct: str, in_reply_to_id: str, text: str) -> None:
        try:
            self._m.status_post(
                f"@{to_acct} {text}",
                in_reply_to_id=in_reply_to_id,
                visibility="direct",
            )
        except Exception as e:
            logging.error("Failed to send DM to %s: %s", to_acct, e)

    def post_gif(self, to_acct: str, in_reply_to_id: str,
                 gif: GifResult, visibility: str) -> None:
        label = "🏠" if gif.is_local else "🌐"
        text = f"@{to_acct} {label} {gif.title}\n{gif.url}"
        try:
            self._m.status_post(
                text,
                in_reply_to_id=in_reply_to_id,
                visibility=visibility,
            )
        except Exception as e:
            logging.error("Failed to post GIF: %s", e)

    def error(self, to_acct: str, in_reply_to_id: str, message: str) -> None:
        self.dm(to_acct, in_reply_to_id, message)

    def gif_list(self, to_acct: str, in_reply_to_id: str,
                 keyword: str, gifs: list[GifResult], offset: int = 0) -> None:
        lines = [f"GIFs for \"{keyword}\":"]
        for i, gif in enumerate(gifs, start=offset + 1):
            label = "🏠 (local)" if gif.is_local else "🌐"
            lines.append(f"{i}. {gif.url}  {label} {gif.title}")
        lines.append("")
        lines.append("Reply: 'send N' to post · 'next' for more · 'block' to ban this GIF · new keyword to search again · 'cancel' to quit")
        self.dm(to_acct, in_reply_to_id, "\n".join(lines))
