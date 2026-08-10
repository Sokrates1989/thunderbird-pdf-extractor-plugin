"""Service tests cover local output, collisions, and cleanup on success and failure."""

from collections.abc import Sequence
from pathlib import Path
from threading import Event

import pytest
from pypdf import PdfReader

from paperless_mail_archiver.archive_service import ArchiveService
from paperless_mail_archiver.errors import HostError
from paperless_mail_archiver.models import ArchiveMetadata, ArchiveRequest, MailDocument
from paperless_mail_archiver.renderers import MailRenderer, ReportLabMailRenderer
from tests.helpers import nested_email_bytes, plain_email_bytes, slice_two_email_bytes


def _request(eml_path: Path, output_directory: Path, file_name: str) -> ArchiveRequest:
    """Build a valid email-only archive request."""
    return ArchiveRequest(
        eml_path=eml_path,
        metadata=ArchiveMetadata(
            title="2026-08-10 - Erika Muster - Rechnung August",
            file_name=file_name,
            include_body=True,
            attachment_count=0,
        ),
        output_directory=output_directory,
        cancellation=Event(),
    )


def test_archive_saves_searchable_pdf_without_overwrite(tmp_path: Path) -> None:
    """A complete PDF is linked into place and a collision receives a numbered name."""
    eml_path = tmp_path / "first.eml"
    eml_path.write_bytes(plain_email_bytes())
    service = ArchiveService(ReportLabMailRenderer())
    first = service.archive(_request(eml_path, tmp_path, "invoice.pdf"), lambda *_: None)

    second_eml = tmp_path / "second.eml"
    second_eml.write_bytes(plain_email_bytes(body="Second body"))
    second = service.archive(_request(second_eml, tmp_path, "invoice.pdf"), lambda *_: None)

    assert first.output_path.name == "invoice.pdf"
    assert second.output_path.name == "invoice (2).pdf"
    assert first.output_path.read_bytes() != b""
    reader = PdfReader(first.output_path)
    assert len(reader.pages) >= 1
    assert reader.metadata is not None
    assert reader.metadata.title == "2026-08-10 - Erika Muster - Rechnung August"
    assert not eml_path.exists()
    assert not second_eml.exists()


class _FailingRenderer(MailRenderer):
    """Renderer that proves orchestration cleanup on a coded failure."""

    def render(
        self,
        document: MailDocument,
        target: Path,
        cancellation: Event,
        *,
        include_body: bool,
        image_mode: str,
    ) -> None:
        """Write a partial file and fail before persistence."""
        del document, cancellation, include_body, image_mode
        target.write_bytes(b"partial")
        raise HostError("render_failed", "Rendering failed safely.")


def test_archive_cleans_eml_and_temporary_pdf_on_failure(tmp_path: Path) -> None:
    """No source EML or partial PDF survives a rendering error."""
    eml_path = tmp_path / "failure.eml"
    eml_path.write_bytes(plain_email_bytes())

    with pytest.raises(HostError, match="failed safely"):
        ArchiveService(_FailingRenderer()).archive(
            _request(eml_path, tmp_path, "failure.pdf"),
            lambda *_: None,
        )

    assert not eml_path.exists()
    assert not (tmp_path / "failure.pdf").exists()


def test_archive_merges_selected_attachments_in_mime_order(tmp_path: Path) -> None:
    """Email, PDF, image, and CSV sections stay ordered while unsupported ZIP is disclosed."""
    eml_path = tmp_path / "slice-two.eml"
    eml_path.write_bytes(slice_two_email_bytes())
    request = ArchiveRequest(
        eml_path=eml_path,
        metadata=ArchiveMetadata(
            title="Slice 2 merged document",
            file_name="slice-two.pdf",
            include_body=True,
            attachment_count=4,
            selected_attachment_indices=(0, 1, 2),
        ),
        output_directory=tmp_path,
        cancellation=Event(),
    )

    result = ArchiveService(ReportLabMailRenderer()).archive(request, lambda *_: None)
    reader = PdfReader(result.output_path)
    extracted_pages = [page.extract_text() or "" for page in reader.pages]

    assert result.included_attachments == (
        "01-original.pdf",
        "02-scan.png",
        "03-data.csv",
    )
    assert result.skipped_attachments == ("04-archive.zip",)
    assert "EMAIL BODY FIRST" in extracted_pages[0]
    assert "Included in the merged PDF" in extracted_pages[0]
    assert "This file type is not supported" in extracted_pages[0]
    assert "ORIGINAL PDF ATTACHMENT" in extracted_pages[1]
    assert "alpha,beta" in extracted_pages[3]
    assert float(reader.pages[1].mediabox.width) == pytest.approx(792)
    assert float(reader.pages[1].mediabox.height) == pytest.approx(612)
    assert "/Annots" not in reader.pages[1]
    outline_titles = [item.title for item in reader.outline if not isinstance(item, list)]
    assert outline_titles == ["E-Mail", "01-original.pdf", "02-scan.png", "03-data.csv"]
    assert reader.metadata is not None
    assert reader.metadata.title == "Slice 2 merged document"


def test_archive_recursively_merges_nested_eml_attachments(tmp_path: Path) -> None:
    """A selected EML becomes an outlined section with its supported children beneath it."""
    eml_path = tmp_path / "nested.eml"
    eml_path.write_bytes(nested_email_bytes())
    request = ArchiveRequest(
        eml_path=eml_path,
        metadata=ArchiveMetadata(
            title="Nested archive",
            file_name="nested.pdf",
            include_body=True,
            attachment_count=1,
            selected_attachment_indices=(0,),
        ),
        output_directory=tmp_path,
        cancellation=Event(),
    )

    result = ArchiveService(ReportLabMailRenderer()).archive(request, lambda *_: None)
    reader = PdfReader(result.output_path)
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    outline_titles: list[str] = []

    def collect_titles(items: Sequence[object]) -> None:
        for item in items:
            if isinstance(item, list):
                collect_titles(item)
            elif hasattr(item, "title"):
                outline_titles.append(str(item.title))

    collect_titles(reader.outline)

    assert "OUTER EMAIL BODY" in extracted
    assert "NESTED EMAIL BODY" in extracted
    assert "NESTED TEXT ATTACHMENT" in extracted
    assert outline_titles == ["E-Mail", "forwarded.eml", "inside.txt"]


def test_optional_separator_page_precedes_selected_attachment(tmp_path: Path) -> None:
    """Separator pages remain opt-in and become the attachment outline destination."""
    eml_path = tmp_path / "separator.eml"
    eml_path.write_bytes(slice_two_email_bytes())
    request = ArchiveRequest(
        eml_path=eml_path,
        metadata=ArchiveMetadata(
            title="With separator",
            file_name="separator.pdf",
            include_body=True,
            attachment_count=4,
            selected_attachment_indices=(0,),
            separator_pages=True,
        ),
        output_directory=tmp_path,
        cancellation=Event(),
    )

    result = ArchiveService(ReportLabMailRenderer()).archive(request, lambda *_: None)
    reader = PdfReader(result.output_path)

    assert len(reader.pages) == 3
    assert "01-original.pdf" in (reader.pages[1].extract_text() or "")
    attachment_destination = reader.outline[1]
    assert not isinstance(attachment_destination, list)
    assert reader.get_destination_page_number(attachment_destination) == 1
