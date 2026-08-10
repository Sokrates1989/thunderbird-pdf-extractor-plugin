"""Bounded local converters for the reviewed Slice 2 attachment formats."""

from __future__ import annotations

import warnings
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from threading import Event
from xml.sax.saxutils import escape as xml_escape

from PIL import Image, ImageOps, ImageSequence, UnidentifiedImageError
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer

from paperless_mail_archiver.attachment_support import attachment_support
from paperless_mail_archiver.email_parser import parse_email
from paperless_mail_archiver.errors import CancelledError, HostError
from paperless_mail_archiver.html_sanitizer import sanitize_html
from paperless_mail_archiver.libreoffice_converter import convert_office_attachment
from paperless_mail_archiver.models import (
    AttachmentDecision,
    AttachmentInfo,
    ImageMode,
    MailDocument,
)
from paperless_mail_archiver.pdf_assembler import (
    PdfSection,
    normalize_selected_pdf,
    validate_attachment_pdf,
)
from paperless_mail_archiver.renderers import MailRenderer, register_unicode_font

MAX_IMAGE_FRAMES = 100
MAX_IMAGE_PIXELS_PER_FRAME = 80_000_000
MAX_IMAGE_PIXELS_TOTAL = 160_000_000
MAX_NESTED_EML_DEPTH = 3


class AttachmentConverter:
    """Convert one selected MIME attachment and recursively supported EML children."""

    def __init__(self, renderer: MailRenderer, libreoffice_executable: Path | None) -> None:
        """Retain explicit local dependencies so support and tests stay deterministic."""
        self._renderer = renderer
        self._libreoffice_executable = libreoffice_executable
        self._sequence = 0

    def convert(
        self,
        attachment: AttachmentInfo,
        workspace: Path,
        cancellation: Event,
        *,
        image_mode: ImageMode,
        depth: int = 0,
    ) -> PdfSection:
        """Convert one supported attachment or fail with its bounded display filename."""
        self._check_cancelled(cancellation)
        support = attachment_support(attachment, self._libreoffice_executable)
        if not support.supported:
            raise HostError(
                "unsupported_attachment",
                f"{attachment.name}: {support.detail}",
            )
        target = self._next_target(workspace)
        try:
            if support.kind == "pdf":
                target.write_bytes(attachment.data)
                normalize_selected_pdf(target, attachment.name)
                return PdfSection(attachment.name, target)
            if support.kind == "image":
                self._convert_image(attachment, target, cancellation)
                return PdfSection(attachment.name, target)
            if support.kind == "text":
                self._convert_text(attachment, target, cancellation)
                return PdfSection(attachment.name, target)
            if support.kind == "html":
                self._convert_html(attachment, target, cancellation)
                return PdfSection(attachment.name, target)
            if support.kind == "eml":
                return self._convert_eml(
                    attachment,
                    target,
                    workspace,
                    cancellation,
                    image_mode=image_mode,
                    depth=depth,
                )
            if support.kind == "office":
                convert_office_attachment(
                    attachment,
                    target,
                    workspace,
                    cancellation,
                    self._libreoffice_executable,
                    self._sequence,
                )
                return PdfSection(attachment.name, target)
        except (CancelledError, HostError):
            target.unlink(missing_ok=True)
            raise
        except (OSError, ValueError) as error:
            target.unlink(missing_ok=True)
            raise HostError(
                "attachment_conversion_failed",
                f"{attachment.name}: conversion failed safely.",
            ) from error
        raise HostError(
            "unsupported_attachment",
            f"{attachment.name}: this file type is not supported.",
        )

    def _next_target(self, workspace: Path) -> Path:
        """Allocate a deterministic unique path inside the owned job workspace."""
        self._sequence += 1
        return workspace / f"attachment-{self._sequence:04d}.pdf"

    def _convert_image(
        self,
        attachment: AttachmentInfo,
        target: Path,
        cancellation: Event,
    ) -> None:
        """Render bounded raster frames with EXIF orientation and preserved aspect ratio."""
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(attachment.data)) as source:
                    pdf_canvas = canvas.Canvas(str(target), pagesize=A4)
                    total_pixels = 0
                    frame_count = 0
                    for raw_frame in ImageSequence.Iterator(source):
                        self._check_cancelled(cancellation)
                        frame_count += 1
                        if frame_count > MAX_IMAGE_FRAMES:
                            raise HostError(
                                "image_too_complex",
                                f"{attachment.name}: the image contains too many frames.",
                            )
                        frame = ImageOps.exif_transpose(raw_frame.copy())
                        pixels = frame.width * frame.height
                        total_pixels += pixels
                        if (
                            pixels > MAX_IMAGE_PIXELS_PER_FRAME
                            or total_pixels > MAX_IMAGE_PIXELS_TOTAL
                        ):
                            raise HostError(
                                "image_too_large",
                                f"{attachment.name}: the decoded image exceeds the safe pixel limit.",
                            )
                        if frame.mode not in {"RGB", "L"}:
                            background = Image.new("RGB", frame.size, "white")
                            if "A" in frame.getbands():
                                background.paste(frame, mask=frame.getchannel("A"))
                            else:
                                background.paste(frame.convert("RGB"))
                            frame = background
                        page_size = landscape(A4) if frame.width > frame.height else portrait(A4)
                        pdf_canvas.setPageSize(page_size)
                        page_width, page_height = page_size
                        available_width = page_width - 24 * mm
                        available_height = page_height - 24 * mm
                        scale = min(available_width / frame.width, available_height / frame.height)
                        width = frame.width * scale
                        height = frame.height * scale
                        encoded = BytesIO()
                        frame.save(encoded, format="PNG")
                        encoded.seek(0)
                        pdf_canvas.drawImage(
                            ImageReader(encoded),
                            (page_width - width) / 2,
                            (page_height - height) / 2,
                            width=width,
                            height=height,
                            mask="auto",
                        )
                        pdf_canvas.showPage()
                    if frame_count == 0:
                        raise HostError(
                            "invalid_image_attachment",
                            f"{attachment.name}: the image contains no renderable frames.",
                        )
                    pdf_canvas.save()
        except (
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
            UnidentifiedImageError,
        ) as error:
            raise HostError(
                "invalid_image_attachment",
                f"{attachment.name}: the image is invalid or unsafe to decode.",
            ) from error
        validate_attachment_pdf(target, attachment.name)

    def _convert_text(
        self,
        attachment: AttachmentInfo,
        target: Path,
        cancellation: Event,
    ) -> None:
        """Create a searchable, wrapping PDF for TXT and CSV data."""
        self._check_cancelled(cancellation)
        decoded = self._decode_text(attachment)
        styles = getSampleStyleSheet()
        font_name = register_unicode_font()
        title_style = ParagraphStyle(
            "AttachmentTitle",
            parent=styles["Title"],
            fontName=font_name,
            fontSize=16,
            leading=20,
            alignment=TA_LEFT,
        )
        text_style = ParagraphStyle(
            "AttachmentText",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=8.5,
            leading=11,
            wordWrap="CJK",
        )
        story: list[Flowable] = [
            Paragraph(xml_escape(attachment.name), title_style),
            Spacer(1, 4 * mm),
        ]
        for line in decoded.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            self._check_cancelled(cancellation)
            story.append(Paragraph(xml_escape(line) if line else "&#160;", text_style))
        document = SimpleDocTemplate(
            str(target),
            pagesize=A4,
            rightMargin=14 * mm,
            leftMargin=14 * mm,
            topMargin=14 * mm,
            bottomMargin=14 * mm,
            title=attachment.name,
        )
        document.build(story)
        validate_attachment_pdf(target, attachment.name)

    def _convert_html(
        self,
        attachment: AttachmentInfo,
        target: Path,
        cancellation: Event,
    ) -> None:
        """Sanitize and pass HTML through the same local mail renderer chain."""
        decoded = self._decode_text(attachment)
        document = MailDocument(
            subject=attachment.name,
            sender="",
            recipients="",
            cc="",
            sent_date="",
            message_id="",
            body=sanitize_html(decoded),
            body_kind="html",
            attachments=(),
        )
        self._renderer.render(
            document,
            target,
            cancellation,
            include_body=True,
            image_mode="placeholder",
        )
        validate_attachment_pdf(target, attachment.name)

    def _convert_eml(
        self,
        attachment: AttachmentInfo,
        target: Path,
        workspace: Path,
        cancellation: Event,
        *,
        image_mode: ImageMode,
        depth: int,
    ) -> PdfSection:
        """Render an attached email and recursively include supported descendants."""
        document = parse_email(attachment.data)
        decisions: list[AttachmentDecision] = []
        nested_to_convert: list[AttachmentInfo] = []
        for nested in document.attachments:
            support = attachment_support(nested, self._libreoffice_executable)
            depth_limited = support.kind == "eml" and depth + 1 >= MAX_NESTED_EML_DEPTH
            if support.supported and not depth_limited:
                decisions.append(
                    AttachmentDecision(nested.index, "included", "Included in the merged PDF.")
                )
                nested_to_convert.append(nested)
            else:
                detail = (
                    "Skipped because the nested-email depth limit was reached."
                    if depth_limited
                    else f"Skipped: {support.detail}"
                )
                decisions.append(AttachmentDecision(nested.index, "skipped", detail))
        document = replace(document, attachment_decisions=tuple(decisions))
        self._renderer.render(
            document,
            target,
            cancellation,
            include_body=True,
            image_mode=image_mode,
        )
        validate_attachment_pdf(target, attachment.name)
        children = tuple(
            self.convert(
                nested,
                workspace,
                cancellation,
                image_mode=image_mode,
                depth=depth + 1,
            )
            for nested in nested_to_convert
        )
        return PdfSection(attachment.name, target, children)

    @staticmethod
    def _decode_text(attachment: AttachmentInfo) -> str:
        """Decode a bounded text attachment with safe charset fallback behavior."""
        encodings = [attachment.charset, "utf-8-sig", "utf-8", "cp1252"]
        for encoding in encodings:
            if not encoding:
                continue
            try:
                return attachment.data.decode(encoding)
            except (LookupError, UnicodeDecodeError):
                continue
        return attachment.data.decode("utf-8", errors="replace")

    @staticmethod
    def _check_cancelled(cancellation: Event) -> None:
        """Raise at converter boundaries without leaving a partial final output."""
        if cancellation.is_set():
            raise CancelledError
