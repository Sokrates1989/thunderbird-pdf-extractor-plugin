"""Resolve explicitly requested email images into bounded, self-contained data."""

from __future__ import annotations

import base64
import binascii
import http.client
import ipaddress
import socket
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import PurePosixPath
from threading import Event
from urllib.parse import unquote, urljoin, urlparse

from paperless_mail_archiver.errors import CancelledError
from paperless_mail_archiver.models import InlineImage, MailDocument

MAX_IMAGE_BYTES = 8_000_000
MAX_TOTAL_IMAGE_BYTES = 25_000_000
MAX_IMAGE_SOURCES = 80
MAX_REMOTE_URL_CHARACTERS = 4_096
MAX_DATA_URI_CHARACTERS = 12_000_000
MAX_IMAGE_DIMENSION = 12_000
MAX_IMAGE_PIXELS = 50_000_000
REMOTE_FETCH_BUDGET_SECONDS = 30.0
REMOTE_REQUEST_TIMEOUT_SECONDS = 5.0
READ_CHUNK_BYTES = 64 * 1024


@dataclass(frozen=True, slots=True)
class ResolvedImage:
    """Contain verified raster bytes and the MIME type used by a data URI."""

    content_type: str
    data: bytes


RemoteLoader = Callable[[str, Event, float], ResolvedImage | None]


class _RejectedImage(ValueError):
    """Mark an image source as unsafe or unsupported without failing the archive job."""


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Return redirects to the loader so every destination is validated before use."""

    def redirect_request(
        self,
        request: urllib.request.Request,
        file_pointer: object,
        code: int,
        message: str,
        headers: object,
        new_url: str,
    ) -> None:
        """Disable urllib's automatic redirect following."""
        del request, file_pointer, code, message, headers, new_url
        return None


def _raster_type_and_dimensions(data: bytes) -> tuple[str, int, int] | None:
    """Identify a supported raster format and return trustworthy header dimensions."""
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return "image/png", int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if data[:6] in {b"GIF87a", b"GIF89a"} and len(data) >= 10:
        return (
            "image/gif",
            int.from_bytes(data[6:8], "little"),
            int.from_bytes(data[8:10], "little"),
        )
    if data.startswith(b"\xff\xd8"):
        dimensions = _jpeg_dimensions(data)
        if dimensions is not None:
            return "image/jpeg", dimensions[0], dimensions[1]
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        dimensions = _webp_dimensions(data)
        if dimensions is not None:
            return "image/webp", dimensions[0], dimensions[1]
    return None


def _jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    """Read JPEG dimensions from a start-of-frame marker without decoding pixels."""
    start_of_frame = frozenset(
        {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    )
    offset = 2
    while offset + 4 <= len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            return None
        marker = data[offset]
        offset += 1
        if marker in {0x01, 0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        if offset + 2 > len(data):
            return None
        segment_length = int.from_bytes(data[offset : offset + 2], "big")
        if segment_length < 2 or offset + segment_length > len(data):
            return None
        if marker in start_of_frame and segment_length >= 7:
            height = int.from_bytes(data[offset + 3 : offset + 5], "big")
            width = int.from_bytes(data[offset + 5 : offset + 7], "big")
            return width, height
        offset += segment_length
    return None


def _webp_dimensions(data: bytes) -> tuple[int, int] | None:
    """Read dimensions from the bounded headers of common WebP variants."""
    if len(data) < 30:
        return None
    chunk_type = data[12:16]
    if chunk_type == b"VP8X":
        width = 1 + int.from_bytes(data[24:27], "little")
        height = 1 + int.from_bytes(data[27:30], "little")
        return width, height
    if chunk_type == b"VP8 " and data[23:26] == b"\x9d\x01\x2a":
        width = int.from_bytes(data[26:28], "little") & 0x3FFF
        height = int.from_bytes(data[28:30], "little") & 0x3FFF
        return width, height
    if chunk_type == b"VP8L" and data[20] == 0x2F:
        bits = int.from_bytes(data[21:25], "little")
        width = (bits & 0x3FFF) + 1
        height = ((bits >> 14) & 0x3FFF) + 1
        return width, height
    return None


def _verified_raster(data: bytes) -> ResolvedImage | None:
    """Accept only bounded raster images with sane, non-zero dimensions."""
    if not data or len(data) > MAX_IMAGE_BYTES:
        return None
    detected = _raster_type_and_dimensions(data)
    if detected is None:
        return None
    content_type, width, height = detected
    if (
        width <= 0
        or height <= 0
        or width > MAX_IMAGE_DIMENSION
        or height > MAX_IMAGE_DIMENSION
        or width * height > MAX_IMAGE_PIXELS
    ):
        return None
    return ResolvedImage(content_type=content_type, data=data)


def _validate_remote_url(source: str) -> None:
    """Require a credential-free public HTTPS URL on the default TLS port."""
    if len(source) > MAX_REMOTE_URL_CHARACTERS:
        raise _RejectedImage("The image URL is too long.")
    parsed = urlparse(source)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise _RejectedImage("Only HTTPS image URLs are supported.")
    if parsed.username is not None or parsed.password is not None:
        raise _RejectedImage("Image URLs with credentials are not supported.")
    try:
        port = parsed.port or 443
    except ValueError as error:
        raise _RejectedImage("The image URL port is invalid.") from error
    if port != 443:
        raise _RejectedImage("Only the default HTTPS port is supported.")
    addresses = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    if not addresses:
        raise _RejectedImage("The image host did not resolve.")
    for address in addresses:
        candidate = ipaddress.ip_address(address[4][0])
        if not candidate.is_global:
            raise _RejectedImage("Private and special-purpose image hosts are blocked.")


def _read_remote_response(
    response: object,
    cancellation: Event,
) -> bytes:
    """Read a response incrementally while enforcing cancellation and the byte limit."""
    headers = getattr(response, "headers", None)
    if headers is not None:
        declared_length = headers.get("Content-Length")
        if declared_length is not None:
            try:
                if int(declared_length) > MAX_IMAGE_BYTES:
                    raise _RejectedImage("The remote image is too large.")
            except ValueError as error:
                raise _RejectedImage("The remote image length is invalid.") from error
    read = getattr(response, "read", None)
    if not callable(read):
        raise _RejectedImage("The remote image response is unreadable.")
    chunks: list[bytes] = []
    total = 0
    while True:
        if cancellation.is_set():
            raise CancelledError
        chunk = read(READ_CHUNK_BYTES)
        if not isinstance(chunk, bytes):
            raise _RejectedImage("The remote image response is not binary.")
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > MAX_IMAGE_BYTES:
            raise _RejectedImage("The remote image is too large.")
        chunks.append(chunk)


def fetch_remote_image(source: str, cancellation: Event, timeout: float) -> ResolvedImage | None:
    """Download one public HTTPS raster without cookies, proxies, or automatic redirects."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirectHandler())
    current_url = source
    for _redirect_count in range(4):
        if cancellation.is_set():
            raise CancelledError
        _validate_remote_url(current_url)
        request = urllib.request.Request(  # noqa: S310 - URL is restricted to validated HTTPS.
            current_url,
            headers={"Accept": "image/avif,image/webp,image/png,image/jpeg,image/gif"},
            method="GET",
        )
        try:
            with opener.open(request, timeout=timeout) as response:
                return _verified_raster(_read_remote_response(response, cancellation))
        except urllib.error.HTTPError as error:
            if error.code not in {301, 302, 303, 307, 308}:
                error.close()
                raise
            location = error.headers.get("Location")
            error.close()
            if not location:
                raise _RejectedImage("The remote image redirect has no destination.") from error
            current_url = urljoin(current_url, location)
    raise _RejectedImage("The remote image redirected too many times.")


def _data_uri_image(source: str) -> ResolvedImage | None:
    """Decode a bounded Base64 raster data URI and verify its actual file signature."""
    if len(source) > MAX_DATA_URI_CHARACTERS:
        return None
    metadata, separator, encoded = source.partition(",")
    if not separator or ";base64" not in metadata.lower():
        return None
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return None
    return _verified_raster(decoded)


def _inline_lookup(images: tuple[InlineImage, ...]) -> tuple[dict[str, bytes], dict[str, bytes]]:
    """Index MIME image bytes by normalized Content-ID and exact Content-Location."""
    by_content_id: dict[str, bytes] = {}
    by_location: dict[str, bytes] = {}
    for image in images:
        if image.content_id:
            by_content_id.setdefault(image.content_id, image.data)
        if image.content_location:
            by_location.setdefault(image.content_location, image.data)
    return by_content_id, by_location


class ImageSourceResolver:
    """Resolve HTML image sources with a total budget and per-source failure fallback."""

    def __init__(
        self,
        document: MailDocument,
        cancellation: Event,
        remote_loader: RemoteLoader = fetch_remote_image,
    ) -> None:
        """Initialize MIME indexes, a result cache, and the remote-fetch deadline."""
        self._by_content_id, self._by_location = _inline_lookup(document.inline_images)
        self._cancellation = cancellation
        self._remote_loader = remote_loader
        self._cache: dict[str, ResolvedImage | None] = {}
        self._total_bytes = 0
        self._remote_deadline = time.monotonic() + REMOTE_FETCH_BUDGET_SECONDS

    def resolve(self, source: str) -> ResolvedImage | None:
        """Return a verified image or ``None`` so the sanitizer emits a placeholder."""
        normalized = source.strip()
        if not normalized:
            return None
        cached = self._cache.get(normalized)
        if normalized in self._cache:
            return cached
        if len(self._cache) >= MAX_IMAGE_SOURCES:
            return None
        try:
            resolved = self._resolve_uncached(normalized)
        except CancelledError:
            raise
        except (
            OSError,
            UnicodeError,
            ValueError,
            http.client.HTTPException,
            urllib.error.URLError,
        ):
            resolved = None
        if resolved is not None and self._total_bytes + len(resolved.data) > MAX_TOTAL_IMAGE_BYTES:
            resolved = None
        if resolved is not None:
            self._total_bytes += len(resolved.data)
        self._cache[normalized] = resolved
        return resolved

    def _resolve_uncached(self, source: str) -> ResolvedImage | None:
        """Resolve one data, CID, location, or public HTTPS source without fallback policy."""
        lower_source = source.lower()
        if lower_source.startswith("data:"):
            return _data_uri_image(source)
        if lower_source.startswith("cid:"):
            content_id = unquote(source[4:]).strip().strip("<>").lower()
            data = self._by_content_id.get(content_id)
            return None if data is None else _verified_raster(data)
        location_data = self._by_location.get(source)
        if location_data is not None:
            return _verified_raster(location_data)
        if not lower_source.startswith("https://"):
            return None
        remaining = self._remote_deadline - time.monotonic()
        if remaining <= 0:
            return None
        timeout = min(REMOTE_REQUEST_TIMEOUT_SECONDS, remaining)
        return self._remote_loader(source, self._cancellation, timeout)


def image_to_data_uri(image: ResolvedImage) -> str:
    """Encode verified image bytes for the renderer's data-only CSP."""
    encoded = base64.b64encode(image.data).decode("ascii")
    return f"data:{image.content_type};base64,{encoded}"


def source_file_name(source: str) -> str:
    """Return a short non-sensitive fallback label derived from a source URL path."""
    parsed = urlparse(source)
    if parsed.scheme.lower() == "data":
        return ""
    name = PurePosixPath(unquote(parsed.path)).name
    return name[:120]
