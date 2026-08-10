"""Local Chromium integration test for the no-remote-resource security boundary."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Thread

import pytest
from pypdf import PdfReader

from paperless_mail_archiver.models import InlineImage, MailDocument
from paperless_mail_archiver.renderers import ChromiumMailRenderer, detect_chromium
from tests.helpers import sample_banner_png_bytes


class _CanaryHandler(BaseHTTPRequestHandler):
    """Count any network request that escapes the sanitized local document."""

    requests = 0

    def do_GET(self) -> None:
        """Record a failed canary request without returning user data."""
        type(self).requests += 1
        self.send_response(204)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        """Suppress test-server access logs."""
        del format, args


@pytest.mark.chromium
def test_remote_image_is_never_requested(tmp_path: Path) -> None:
    """The sanitizer and CSP prevent even loopback image loading during PDF print."""
    executable = detect_chromium()
    if executable is None:
        pytest.skip("No supported Chromium browser is installed.")
    server = ThreadingHTTPServer(("127.0.0.1", 0), _CanaryHandler)
    port = server.server_address[1]
    _CanaryHandler.requests = 0
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    document = MailDocument(
        subject="Network isolation",
        sender="sender@example.test",
        recipients="recipient@example.test",
        cc="",
        sent_date="10 Aug 2026",
        message_id="<canary@example.test>",
        body=f'<p>Visible</p><img src="http://127.0.0.1:{port}/pixel" alt="Remote">',
        body_kind="html",
        attachments=(),
    )
    target = tmp_path / "chromium.pdf"
    try:
        ChromiumMailRenderer(executable).render(
            document,
            target,
            Event(),
            include_body=True,
            image_mode="placeholder",
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert target.is_file()
    assert _CanaryHandler.requests == 0


@pytest.mark.chromium
def test_verified_cid_image_is_printed_into_pdf(tmp_path: Path) -> None:
    """Embed mode prints verified MIME image data without granting Chromium network access."""
    executable = detect_chromium()
    if executable is None:
        pytest.skip("No supported Chromium browser is installed.")
    document = MailDocument(
        subject="Embedded image",
        sender="sender@example.test",
        recipients="recipient@example.test",
        cc="",
        sent_date="10 Aug 2026",
        message_id="<embedded@example.test>",
        body='<p>Before image</p><img src="cid:banner@example.test" alt="Banner"><p>After image</p>',
        body_kind="html",
        attachments=(),
        inline_images=(
            InlineImage(
                content_id="banner@example.test",
                content_location="",
                content_type="image/png",
                data=sample_banner_png_bytes(),
            ),
        ),
    )
    target = tmp_path / "embedded-image.pdf"

    ChromiumMailRenderer(executable).render(
        document,
        target,
        Event(),
        include_body=True,
        image_mode="embed",
    )

    reader = PdfReader(target)
    assert len(reader.pages) >= 1
    assert any(page.images for page in reader.pages)
