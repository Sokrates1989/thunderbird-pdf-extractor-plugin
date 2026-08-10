"""Conversion support tests cover native classification and optional Office availability."""

from pathlib import Path

import pytest

from paperless_mail_archiver.attachment_support import attachment_kind, attachment_support
from paperless_mail_archiver.models import AttachmentInfo


def attachment(name: str, content_type: str = "application/octet-stream") -> AttachmentInfo:
    """Build one small attachment model for preflight tests."""
    return AttachmentInfo(0, name, content_type, 1, b"x")


@pytest.mark.parametrize(
    ("name", "content_type", "expected"),
    [
        ("invoice.pdf", "application/octet-stream", "pdf"),
        ("scan.webp", "image/webp", "image"),
        ("data.csv", "text/plain", "text"),
        ("page.html", "text/html", "html"),
        ("forwarded.eml", "message/rfc822", "eml"),
    ],
)
def test_attachment_kind(name: str, content_type: str, expected: str) -> None:
    """Reviewed MIME types and extensions map to the matching converter."""
    assert attachment_kind(name, content_type) == expected


def test_office_support_requires_a_detected_local_executable() -> None:
    """The UI may select Office input only when native preflight reports LibreOffice."""
    document = attachment("report.docx")

    assert attachment_support(document, None).supported is False
    assert attachment_support(document, Path("soffice.exe")).supported is True


def test_archives_remain_explicitly_unsupported() -> None:
    """ZIP input is disclosed rather than expanded or silently dropped."""
    support = attachment_support(attachment("bundle.zip"), None)

    assert support.kind == "unsupported"
    assert support.supported is False
