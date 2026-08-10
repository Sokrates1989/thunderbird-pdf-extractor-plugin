"""Deterministic, non-rasterizing PDF assembly with attachment outlines."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from threading import Event
from xml.sax.saxutils import escape as xml_escape

from pypdf import PasswordType, PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    Fit,
    FloatObject,
    IndirectObject,
    NameObject,
    NumberObject,
    TextStringObject,
)
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from paperless_mail_archiver.errors import CancelledError, HostError
from paperless_mail_archiver.html_sanitizer import safe_link_href
from paperless_mail_archiver.models import MailDocument
from paperless_mail_archiver.renderers import register_unicode_font

MAX_PAGES_PER_SECTION = 5_000
MAX_MERGED_PAGES = 10_000


def _safe_link_annotation(
    reference: IndirectObject | DictionaryObject,
) -> IndirectObject | DictionaryObject | None:
    """Normalize one HTTP(S) or mail link and discard every other PDF action."""
    try:
        annotation = reference.get_object() if hasattr(reference, "get_object") else reference
        if not isinstance(annotation, DictionaryObject) or annotation.get("/Subtype") != "/Link":
            return None
        action_value = annotation.get("/A")
        action = (
            action_value.get_object() if isinstance(action_value, IndirectObject) else action_value
        )
        if not isinstance(action, DictionaryObject) or action.get("/S") != "/URI":
            return None
        uri_value = action.get("/URI")
        if not isinstance(uri_value, str):
            return None
        uri = safe_link_href(uri_value)
        if uri is None:
            return None
        rect_value = annotation.get("/Rect")
        rect = rect_value.get_object() if isinstance(rect_value, IndirectObject) else rect_value
        if not isinstance(rect, ArrayObject) or len(rect) != 4:
            return None
        coordinates = [float(value) for value in rect]
        if not all(abs(value) <= 1_000_000 for value in coordinates):
            return None
    except (OverflowError, PdfReadError, TypeError, ValueError):
        return None

    annotation.clear()
    annotation.update(
        {
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Link"),
            NameObject("/Rect"): ArrayObject(FloatObject(value) for value in coordinates),
            NameObject("/Border"): ArrayObject((NumberObject(0), NumberObject(0), NumberObject(0))),
            NameObject("/Contents"): TextStringObject(uri),
            NameObject("/A"): DictionaryObject(
                {
                    NameObject("/S"): NameObject("/URI"),
                    NameObject("/URI"): TextStringObject(uri),
                }
            ),
        }
    )
    return reference


def _sanitize_page_actions(page: DictionaryObject) -> None:
    """Remove automatic actions while retaining only normalized external URI links."""
    if "/AA" in page:
        del page["/AA"]
    annotation_value = page.get("/Annots")
    annotations = (
        annotation_value.get_object()
        if isinstance(annotation_value, IndirectObject)
        else annotation_value
    )
    if not isinstance(annotations, ArrayObject):
        page.pop("/Annots", None)
        return
    retained = ArrayObject(
        normalized
        for reference in annotations
        if (normalized := _safe_link_annotation(reference)) is not None
    )
    if retained:
        page[NameObject("/Annots")] = retained
    else:
        page.pop("/Annots", None)


@dataclass(frozen=True, slots=True)
class PdfSection:
    """One PDF section and any recursively converted child attachments."""

    title: str
    path: Path
    children: tuple[PdfSection, ...] = ()
    allow_separator: bool = True


def validate_attachment_pdf(
    path: Path,
    attachment_name: str,
    *,
    maximum_pages: int = MAX_PAGES_PER_SECTION,
) -> int:
    """Reject empty, corrupt, or encrypted PDFs with a safe filename-level message."""
    try:
        reader = PdfReader(path, strict=True)
        if reader.is_encrypted:
            raise HostError(
                "encrypted_attachment",
                f"{attachment_name}: encrypted PDF attachments are not supported.",
            )
        page_count = len(reader.pages)
        if page_count < 1:
            raise HostError(
                "empty_attachment_pdf",
                f"{attachment_name}: the converted PDF has no pages.",
            )
        if page_count > maximum_pages:
            raise HostError(
                "attachment_pdf_too_large",
                f"{attachment_name}: the PDF contains too many pages.",
            )
        return page_count
    except HostError:
        raise
    except (PdfReadError, OSError, ValueError) as error:
        raise HostError(
            "invalid_attachment_pdf",
            f"{attachment_name}: the attachment could not be read as a PDF.",
        ) from error


def normalize_selected_pdf(path: Path, attachment_name: str) -> int:
    """Decrypt an empty-password PDF in place while rejecting password-required input."""
    try:
        reader = PdfReader(BytesIO(path.read_bytes()), strict=True)
        if not reader.is_encrypted:
            return validate_attachment_pdf(path, attachment_name)
        if reader.decrypt("") == PasswordType.NOT_DECRYPTED:
            raise HostError(
                "encrypted_attachment",
                f"{attachment_name}: the PDF requires a password and cannot be merged.",
            )
        page_count = len(reader.pages)
        if page_count < 1:
            raise HostError(
                "empty_attachment_pdf",
                f"{attachment_name}: the converted PDF has no pages.",
            )
        if page_count > MAX_PAGES_PER_SECTION:
            raise HostError(
                "attachment_pdf_too_large",
                f"{attachment_name}: the PDF contains too many pages.",
            )
        writer = PdfWriter()
        try:
            writer.append(reader, import_outline=False)
            with path.open("wb") as stream:
                writer.write(stream)
        finally:
            writer.close()
        return validate_attachment_pdf(path, attachment_name)
    except HostError:
        raise
    except (PdfReadError, OSError, ValueError) as error:
        raise HostError(
            "invalid_attachment_pdf",
            f"{attachment_name}: the attachment could not be read as a PDF.",
        ) from error


def _separator_pdf(title: str) -> BytesIO:
    """Create one optional, searchable separator page in memory."""
    output = BytesIO()
    page = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    page.setTitle(title)
    style = ParagraphStyle(
        "SeparatorTitle",
        fontName=register_unicode_font(),
        fontSize=20,
        leading=25,
        alignment=TA_CENTER,
    )
    paragraph = Paragraph(xml_escape(title[:240]), style)
    paragraph_width, paragraph_height = paragraph.wrap(width - 36 * mm, height - 36 * mm)
    paragraph.drawOn(page, (width - paragraph_width) / 2, (height - paragraph_height) / 2)
    page.showPage()
    page.save()
    output.seek(0)
    return output


def assemble_pdf(
    target: Path,
    sections: tuple[PdfSection, ...],
    document: MailDocument,
    *,
    title: str,
    separator_pages: bool,
    cancellation: Event,
) -> int:
    """Merge sections in order, preserving page geometry and adding a navigable outline."""
    writer = PdfWriter()

    def append_section(section: PdfSection, parent: IndirectObject | None = None) -> None:
        if cancellation.is_set():
            raise CancelledError
        validate_attachment_pdf(section.path, section.title)
        first_page = len(writer.pages)
        if separator_pages and section.allow_separator:
            writer.append(_separator_pdf(section.title), import_outline=False)
        writer.append(section.path, import_outline=False)
        outline = writer.add_outline_item(
            section.title,
            first_page,
            parent=parent,
            fit=Fit.fit(),
        )
        for child in section.children:
            append_section(child, outline)

    try:
        for section in sections:
            append_section(section)
        if not writer.pages:
            raise HostError("empty_pdf", "The merged PDF has no pages.")
        if len(writer.pages) > MAX_MERGED_PAGES:
            raise HostError("merged_pdf_too_large", "The merged PDF contains too many pages.")
        for page in writer.pages:
            _sanitize_page_actions(page)
        writer.add_metadata(
            {
                "/Title": title or document.subject,
                "/Author": document.sender,
                "/Subject": "Archived email with attachments",
                "/Keywords": "email, thunderbird, attachments",
            }
        )
        with target.open("wb") as stream:
            writer.write(stream)
        page_count = validate_attachment_pdf(
            target,
            "Merged document",
            maximum_pages=MAX_MERGED_PAGES,
        )
        return page_count
    except HostError:
        target.unlink(missing_ok=True)
        raise
    except (PdfReadError, OSError, ValueError) as error:
        target.unlink(missing_ok=True)
        raise HostError("merge_failed", "The final PDF could not be assembled safely.") from error
    finally:
        writer.close()
