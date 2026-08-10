"""PDF validation and metadata normalization without rasterizing page content."""

from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from paperless_mail_archiver.errors import HostError
from paperless_mail_archiver.models import MailDocument


def validate_and_tag_pdf(path: Path, document: MailDocument, *, title: str | None = None) -> int:
    """Validate pages, add searchable-document metadata, and return the page count."""
    try:
        reader = PdfReader(path, strict=True)
        if len(reader.pages) == 0:
            raise HostError("empty_pdf", "The renderer produced a PDF with no pages.")
        writer = PdfWriter()
        writer.append_pages_from_reader(reader)
        writer.add_metadata(
            {
                "/Title": title or document.subject,
                "/Author": document.sender,
                "/Subject": "Archived email",
                "/Keywords": "email, thunderbird",
            }
        )
        replacement = path.with_suffix(".normalized.pdf")
        with replacement.open("wb") as stream:
            writer.write(stream)
        replacement.replace(path)
        return len(reader.pages)
    except (PdfReadError, OSError, ValueError) as error:
        path.unlink(missing_ok=True)
        raise HostError("invalid_rendered_pdf", "The renderer produced an invalid PDF.") from error
