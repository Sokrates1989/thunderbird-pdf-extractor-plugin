"""Strict allow-list sanitizer that never retains remote-loadable email resources."""

from __future__ import annotations

import html
from collections.abc import Callable
from html.parser import HTMLParser
from urllib.parse import urlparse

from paperless_mail_archiver.image_resources import (
    ResolvedImage,
    image_to_data_uri,
    source_file_name,
)

ALLOWED_TAGS = frozenset(
    {
        "a",
        "b",
        "blockquote",
        "br",
        "code",
        "div",
        "em",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "i",
        "li",
        "ol",
        "p",
        "pre",
        "span",
        "strong",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "u",
        "ul",
    }
)
VOID_TAGS = frozenset({"br", "hr"})
FORBIDDEN_CONTAINERS = frozenset(
    {"applet", "embed", "form", "iframe", "math", "object", "script", "style", "svg"}
)
SAFE_LINK_SCHEMES = frozenset({"http", "https", "mailto"})
MAX_ALTERNATIVE_TEXT_CHARACTERS = 200
MAX_LINK_URL_CHARACTERS = 4_096

ImageResolver = Callable[[str], ResolvedImage | None]


def safe_link_href(candidate: str) -> str | None:
    """Return a bounded external link when its scheme and authority are safe."""
    href = candidate.strip()
    if not href or len(href) > MAX_LINK_URL_CHARACTERS:
        return None
    if any(ord(character) < 32 or ord(character) == 127 for character in href):
        return None
    try:
        parsed = urlparse(href)
        scheme = parsed.scheme.lower()
        if scheme not in SAFE_LINK_SCHEMES:
            return None
        if scheme in {"http", "https"}:
            if not parsed.hostname or parsed.username is not None or parsed.password is not None:
                return None
        elif not parsed.path:
            return None
    except (UnicodeError, ValueError):
        return None
    return href


class _Sanitizer(HTMLParser):
    """Emit only structural markup and safe links from an email fragment."""

    def __init__(self, image_resolver: ImageResolver | None) -> None:
        """Initialize the parser, output buffer, and forbidden nesting depth."""
        super().__init__(convert_charrefs=True)
        self.output: list[str] = []
        self.forbidden_depth = 0
        self.image_resolver = image_resolver
        self.open_anchor_indices: list[int] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Allow safe structure and turn every image into embedded data or a placeholder."""
        normalized = tag.lower()
        if normalized in FORBIDDEN_CONTAINERS:
            self.forbidden_depth += 1
            return
        if self.forbidden_depth > 0:
            return
        attributes = {name.lower(): value for name, value in attrs}
        if normalized == "img":
            source = (attributes.get("src") or "").strip()
            alternative = (attributes.get("alt") or "").strip()
            label = (alternative or source_file_name(source) or "Image")[
                :MAX_ALTERNATIVE_TEXT_CHARACTERS
            ]
            resolved = self.image_resolver(source) if self.image_resolver is not None else None
            if resolved is None:
                placeholder = f'<span class="image-placeholder">[{html.escape(label)}]</span>'
                source_href = safe_link_href(source)
                if (
                    source_href is not None
                    and urlparse(source_href).scheme.lower()
                    in {
                        "http",
                        "https",
                    }
                    and not self.open_anchor_indices
                ):
                    escaped_href = html.escape(source_href, quote=True)
                    self.output.append(
                        f'<a class="image-link" href="{escaped_href}">{placeholder}</a>'
                    )
                else:
                    self.output.append(placeholder)
            else:
                data_uri = image_to_data_uri(resolved)
                self.output.append(f'<img src="{data_uri}" alt="{html.escape(label, quote=True)}">')
            if self.open_anchor_indices:
                anchor_index = self.open_anchor_indices[-1]
                opening = self.output[anchor_index]
                if 'class="image-link"' not in opening:
                    self.output[anchor_index] = opening.replace("<a ", '<a class="image-link" ', 1)
            return
        if normalized not in ALLOWED_TAGS:
            return
        if normalized == "a":
            href = attributes.get("href") or ""
            safe_href = safe_link_href(href)
            if safe_href is not None:
                self.output.append(f'<a href="{html.escape(safe_href, quote=True)}">')
                self.open_anchor_indices.append(len(self.output) - 1)
                return
            self.output.append("<a>")
            self.open_anchor_indices.append(len(self.output) - 1)
            return
        self.output.append(f"<{normalized}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Process an XHTML-style void element through the same allow-list."""
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        """Close only allowed non-void tags outside forbidden containers."""
        normalized = tag.lower()
        if normalized in FORBIDDEN_CONTAINERS:
            if self.forbidden_depth > 0:
                self.forbidden_depth -= 1
            return
        if self.forbidden_depth == 0 and normalized in ALLOWED_TAGS and normalized not in VOID_TAGS:
            if normalized == "a" and self.open_anchor_indices:
                self.open_anchor_indices.pop()
            self.output.append(f"</{normalized}>")

    def handle_data(self, data: str) -> None:
        """Escape all retained text content."""
        if self.forbidden_depth == 0:
            self.output.append(html.escape(data))


def sanitize_html(fragment: str, image_resolver: ImageResolver | None = None) -> str:
    """Return safe HTML containing only caller-resolved image data and no remote resources."""
    parser = _Sanitizer(image_resolver)
    parser.feed(fragment)
    parser.close()
    return "".join(parser.output)


class _TextExtractor(HTMLParser):
    """Extract readable fallback text while preserving basic block boundaries."""

    _BLOCK_TAGS = frozenset({"br", "div", "h1", "h2", "h3", "h4", "li", "p", "tr"})

    def __init__(self) -> None:
        """Initialize an empty text buffer."""
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Insert a boundary before block-level content."""
        del attrs
        if tag.lower() in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        """Insert a boundary after block-level content."""
        if tag.lower() in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        """Retain visible text from the already-sanitized fragment."""
        self.parts.append(data)


def html_to_text(sanitized_fragment: str) -> str:
    """Convert sanitized HTML to deterministic readable fallback text."""
    parser = _TextExtractor()
    parser.feed(sanitized_fragment)
    parser.close()
    lines = (" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    return "\n".join(line for line in lines if line)
