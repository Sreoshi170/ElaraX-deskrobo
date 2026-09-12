"""Safe text normalization for email content shown to users or sent to TTS."""

from html import unescape
from html.parser import HTMLParser
import re


class _VisibleTextParser(HTMLParser):
    _hidden_tags = {"head", "script", "style", "svg", "title"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._hidden_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() in self._hidden_tags:
            self._hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in self._hidden_tags and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._hidden_depth:
            self.parts.append(data)


def sanitize_email_content(content: object, *, max_length: int = 2_000) -> str:
    """Return compact visible email text without HTML, CSS, or script content."""

    source = str(content or "")
    parser = _VisibleTextParser()
    try:
        parser.feed(source)
        parser.close()
        visible = " ".join(parser.parts) if "<" in source else source
    except Exception:
        visible = source

    visible = unescape(visible)
    # Handle malformed/plain-text marketing CSS that was not wrapped in a style tag.
    visible = re.sub(r"@(?:media|font-face|supports)[^{]*\{.*?\}", " ", visible, flags=re.IGNORECASE | re.DOTALL)
    visible = re.sub(r"(?:^|\s)[.#]?[a-z][\w\s,#.:-]*\{[^{}]*\}", " ", visible, flags=re.IGNORECASE)
    visible = re.sub(r"<[^>]*>", " ", visible)
    visible = re.sub(r"\s+", " ", visible).strip()
    if len(visible) > max_length:
        return visible[: max(1, max_length - 1)].rstrip() + "…"
    return visible
