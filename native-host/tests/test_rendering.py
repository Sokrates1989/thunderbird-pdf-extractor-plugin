"""Rendering tests verify extractable text, metadata, safe HTML, and attachment disclosure."""

from dataclasses import replace
from pathlib import Path
from threading import Event

from pypdf import PdfReader

from paperless_mail_archiver.email_parser import parse_email
from paperless_mail_archiver.image_resources import ImageSourceResolver
from paperless_mail_archiver.models import AttachmentDecision
from paperless_mail_archiver.pdf_utils import validate_and_tag_pdf
from paperless_mail_archiver.renderers import (
    ReportLabMailRenderer,
    _pdf_output_is_complete,
    build_safe_html,
)
from tests.helpers import attachment_email_bytes, plain_email_bytes


def test_reportlab_pdf_is_searchable_and_contains_no_raw_mime(tmp_path: Path) -> None:
    """The normalized PDF exposes decoded mail text but no MIME headers or Base64 payload."""
    document = parse_email(plain_email_bytes())
    target = tmp_path / "email.pdf"
    ReportLabMailRenderer().render(
        document,
        target,
        Event(),
        include_body=True,
        image_mode="placeholder",
    )
    page_count = validate_and_tag_pdf(target, document)
    reader = PdfReader(target)
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert page_count >= 1
    assert "Rechnung August" in extracted
    assert "20.08.2026" in extracted
    assert "Content-Transfer-Encoding" not in extracted
    assert reader.metadata is not None
    assert reader.metadata.title == document.subject


def test_chromium_output_requires_a_complete_pdf_marker(tmp_path: Path) -> None:
    """A renderer process may be stopped only after a full PDF has been flushed."""
    target = tmp_path / "chromium.pdf"
    target.write_bytes(b"%PDF-1.7\n" + b"x" * 128)

    assert _pdf_output_is_complete(target) is False

    target.write_bytes(b"%PDF-1.7\n" + b"x" * 128 + b"\n%%EOF\n")

    assert _pdf_output_is_complete(target) is True


def test_safe_html_discloses_but_does_not_embed_attachment() -> None:
    """Placeholder mode names skipped attachments without embedding inline image bytes."""
    document = parse_email(attachment_email_bytes())
    document = replace(
        document,
        attachment_decisions=(AttachmentDecision(0, "included", "Included in the merged PDF."),),
    )
    rendered = build_safe_html(document, include_body=True)

    assert "invoice.pdf" in rendered
    assert "Included in the merged PDF" in rendered
    assert "pixel.png" not in rendered
    assert "cid:pixel@example.test" not in rendered


def test_safe_html_prints_link_labels_without_appending_raw_urls() -> None:
    """Long tracking destinations stay interactive without expanding the printed layout."""
    document = parse_email(plain_email_bytes())
    document = replace(
        document,
        body=(
            '<a href="https://click.example.test/very/long/tracking/destination">'
            "Geschnetzeltes Züricher Art mit Spätzle</a>"
        ),
        body_kind="html",
    )

    rendered = build_safe_html(document, include_body=True)

    assert "Geschnetzeltes Züricher Art mit Spätzle</a>" in rendered
    assert "attr(href)" not in rendered


def test_safe_html_embeds_verified_cid_image_as_data() -> None:
    """Embed mode resolves a CID image locally while preserving the data-only CSP."""
    document = parse_email(attachment_email_bytes())
    resolver = ImageSourceResolver(document, Event())

    rendered = build_safe_html(document, include_body=True, image_resolver=resolver)

    assert 'img src="data:image/png;base64,' in rendered
    assert "cid:pixel@example.test" not in rendered
    assert "img-src data:" in rendered
