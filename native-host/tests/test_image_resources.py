"""Image resolution tests cover local embedding, remote fallback, and bounded formats."""

from http.client import IncompleteRead
from threading import Event

from paperless_mail_archiver.image_resources import ImageSourceResolver, ResolvedImage
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
