"""MIME parsing tests cover body choice, Unicode, and real attachment detection."""

from paperless_mail_archiver.email_parser import parse_email
from tests.helpers import (
    alternative_email_bytes,
    attachment_email_bytes,
    nested_email_bytes,
    plain_email_bytes,
)


def test_plain_email_decodes_german_headers_and_body() -> None:
    """Declared UTF-8 content remains readable for PDF search."""
    document = parse_email(plain_email_bytes())

    assert document.subject == "Rechnung August – Büromaterial"  # noqa: RUF001 - Fixture.
    assert "Empfänger" in document.recipients
    assert "bezahlen" in document.body
    assert document.body_kind == "plain"


def test_multipart_alternative_selects_only_html() -> None:
    """The HTML alternative is preferred without duplicating the plain version."""
    document = parse_email(alternative_email_bytes())

    assert document.body_kind == "html"
    assert "HTML version is selected" in document.body
    assert "PLAIN VERSION MUST NOT APPEAR" not in document.body


def test_inline_image_is_not_a_real_attachment() -> None:
    """Inline logo/tracker MIME parts are excluded from the attachment list."""
    document = parse_email(attachment_email_bytes())

    assert [attachment.name for attachment in document.attachments] == ["invoice.pdf"]
    assert len(document.inline_images) == 1
    assert document.inline_images[0].content_id == "pixel@example.test"


def test_nested_message_is_one_top_level_attachment() -> None:
    """Top-level MIME order is not polluted by recursively walking inside attached EML files."""
    document = parse_email(nested_email_bytes())

    assert [attachment.name for attachment in document.attachments] == ["forwarded.eml"]
    assert document.attachments[0].content_type == "message/rfc822"
    assert b"NESTED EMAIL BODY" in document.attachments[0].data
