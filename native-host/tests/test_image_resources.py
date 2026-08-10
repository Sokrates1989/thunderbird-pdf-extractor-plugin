"""Image resolution tests cover local embedding, remote fallback, and bounded formats."""

from http.client import IncompleteRead
from threading import Event
from types import TracebackType
from typing import Self
from urllib import request as urllib_request
from urllib.request import Request

import pytest

import paperless_mail_archiver.image_resources as image_resources
from paperless_mail_archiver.image_resources import (
    REMOTE_IMAGE_ACCEPT,
    ImageSourceResolver,
    ResolvedImage,
    fetch_remote_image,
    source_file_name,
)
from paperless_mail_archiver.models import InlineImage, MailDocument
from tests.helpers import VALID_PNG


def _document(*, body: str, inline_images: tuple[InlineImage, ...] = ()) -> MailDocument:
    """Build the smallest HTML document required by the source resolver."""
    return MailDocument(
        subject="Images",
        sender="sender@example.test",
        recipients="recipient@example.test",
        cc="",
        sent_date="10 Aug 2026",
        message_id="<images@example.test>",
        body=body,
        body_kind="html",
        attachments=(),
        inline_images=inline_images,
    )


def test_cid_image_resolves_from_mime_without_network() -> None:
    """A normalized Content-ID maps to its verified MIME raster bytes."""
    document = _document(
        body='<img src="cid:logo@example.test">',
        inline_images=(
            InlineImage(
                content_id="logo@example.test",
                content_location="",
                content_type="image/png",
                data=VALID_PNG,
            ),
        ),
    )
    resolver = ImageSourceResolver(document, Event())

    assert resolver.resolve("cid:logo@example.test") == ResolvedImage(
        content_type="image/png",
        data=VALID_PNG,
    )


def test_remote_failure_returns_placeholder_signal() -> None:
    """A failed HTTPS fetch becomes ``None`` instead of aborting PDF creation."""
    calls: list[str] = []

    def failing_loader(source: str, cancellation: Event, timeout: float) -> None:
        del cancellation, timeout
        calls.append(source)
        raise OSError("offline")

    resolver = ImageSourceResolver(
        _document(body=""),
        Event(),
        remote_loader=failing_loader,
    )

    assert resolver.resolve("https://images.example.test/banner.png") is None
    assert calls == ["https://images.example.test/banner.png"]
    assert resolver.resolve("https://images.example.test/banner.png") is None
    assert calls == ["https://images.example.test/banner.png"]


def test_incomplete_http_image_returns_placeholder_signal() -> None:
    """A truncated HTTP response remains a per-image fallback instead of aborting the job."""

    def incomplete_loader(source: str, cancellation: Event, timeout: float) -> None:
        del source, cancellation, timeout
        raise IncompleteRead(b"partial", 100)

    resolver = ImageSourceResolver(
        _document(body=""),
        Event(),
        remote_loader=incomplete_loader,
    )

    assert resolver.resolve("https://images.example.test/banner.png") is None


def test_http_source_is_rejected_without_calling_remote_loader() -> None:
    """Only HTTPS sources can cross the explicit remote-image boundary."""
    called = False

    def loader(source: str, cancellation: Event, timeout: float) -> ResolvedImage:
        del source, cancellation, timeout
        nonlocal called
        called = True
        return ResolvedImage(content_type="image/png", data=VALID_PNG)

    resolver = ImageSourceResolver(_document(body=""), Event(), remote_loader=loader)

    assert resolver.resolve("http://images.example.test/banner.png") is None
    assert called is False


def test_remote_request_advertises_only_formats_the_verifier_accepts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A server cannot negotiate AVIF when the local verifier cannot validate it."""
    requests: list[Request] = []

    class _Response:
        """Serve one verified PNG through urllib's context-manager boundary."""

        def __init__(self) -> None:
            self.headers: dict[str, str] = {}
            self._read = False

        def __enter__(self) -> Self:
            return self

        def __exit__(
            self,
            exception_type: type[BaseException] | None,
            exception: BaseException | None,
            traceback: TracebackType | None,
        ) -> None:
            del exception_type, exception, traceback

        def read(self, size: int) -> bytes:
            del size
            if self._read:
                return b""
            self._read = True
            return VALID_PNG

    class _Opener:
        """Capture the outgoing request without crossing the network boundary."""

        def open(self, request: Request, timeout: float) -> _Response:
            del timeout
            requests.append(request)
            return _Response()

    monkeypatch.setattr(image_resources, "_validate_remote_url", lambda _source: None)
    monkeypatch.setattr(urllib_request, "build_opener", lambda *_args: _Opener())

    result = fetch_remote_image("https://images.example.test/banner.png", Event(), 1.0)

    assert result is not None
    assert requests[0].get_header("Accept") == REMOTE_IMAGE_ACCEPT
    assert "avif" not in REMOTE_IMAGE_ACCEPT


def test_remote_fallback_label_hides_opaque_tracking_tokens() -> None:
    """An unlabelled tracking URL cannot leak its opaque path into the PDF layout."""
    assert source_file_name("https://images.example.test/assets/recipe.png") == "recipe.png"
    assert source_file_name("https://click.example.test/opaqueTrackingTokenWithoutExtension") == ""
