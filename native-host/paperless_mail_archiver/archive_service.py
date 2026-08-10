"""Orchestrate verified EML parsing, rendering, PDF validation, and local persistence."""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from paperless_mail_archiver.attachment_converter import AttachmentConverter
from paperless_mail_archiver.attachment_support import attachment_support, detect_libreoffice
from paperless_mail_archiver.email_parser import parse_email
from paperless_mail_archiver.errors import CancelledError, HostError
from paperless_mail_archiver.models import ArchiveRequest, ArchiveResult, AttachmentDecision
from paperless_mail_archiver.output_store import store_pdf
from paperless_mail_archiver.pdf_assembler import PdfSection, assemble_pdf
from paperless_mail_archiver.renderers import (
    ChromiumMailRenderer,
    FallbackMailRenderer,
    MailRenderer,
    ReportLabMailRenderer,
)

ProgressCallback = Callable[[str, int, int, str], None]


class ArchiveService:
    """Execute one side-effect-bounded local email archive operation."""

    def __init__(
        self,
        renderer: MailRenderer | None = None,
        libreoffice_executable: Path | None = None,
    ) -> None:
        """Use the production renderer chain unless a test supplies one explicitly."""
        self._renderer = renderer or FallbackMailRenderer(
            ChromiumMailRenderer(),
            ReportLabMailRenderer(),
        )
        self._libreoffice_executable = libreoffice_executable or detect_libreoffice()

    def archive(self, request: ArchiveRequest, progress: ProgressCallback) -> ArchiveResult:
        """Create and persist one searchable merged PDF, cleaning all temporary data."""
        try:
            self._check_cancelled(request)
            progress("parsing", 0, 1, "")
            raw_message = request.eml_path.read_bytes()
            document = parse_email(raw_message)
            self._validate_attachment_selection(request, len(document.attachments))
            selected_indices = set(request.metadata.selected_attachment_indices)
            decisions: list[AttachmentDecision] = []
            selected_attachments = []
            for attachment in document.attachments:
                support = attachment_support(attachment, self._libreoffice_executable)
                if attachment.index in selected_indices:
                    if not support.supported:
                        raise HostError(
                            "unsupported_attachment",
                            f"{attachment.name}: {support.detail}",
                        )
                    decisions.append(
                        AttachmentDecision(
                            attachment.index,
                            "included",
                            "Included in the merged PDF.",
                        )
                    )
                    selected_attachments.append(attachment)
                else:
                    detail = (
                        "Skipped by the user."
                        if support.supported
                        else f"Skipped: {support.detail}"
                    )
                    decisions.append(AttachmentDecision(attachment.index, "skipped", detail))
            document = replace(document, attachment_decisions=tuple(decisions))
            progress("parsing", 1, 1, "")
            self._check_cancelled(request)

            with tempfile.TemporaryDirectory(prefix="tb-archive-") as temporary_directory:
                workspace = Path(temporary_directory)
                rendered_pdf = workspace / "email.pdf"
                progress("rendering", 0, 1, "")
                self._renderer.render(
                    document,
                    rendered_pdf,
                    request.cancellation,
                    include_body=request.metadata.include_body,
                    image_mode=request.metadata.image_mode,
                )
                progress("rendering", 1, 1, "")
                self._check_cancelled(request)
                converter = AttachmentConverter(self._renderer, self._libreoffice_executable)
                converted: list[PdfSection] = []
                total_attachments = len(selected_attachments)
                for completed, attachment in enumerate(selected_attachments):
                    progress("converting", completed, total_attachments, attachment.name)
                    converted.append(
                        converter.convert(
                            attachment,
                            workspace,
                            request.cancellation,
                            image_mode=request.metadata.image_mode,
                        )
                    )
                progress("converting", total_attachments, total_attachments, "")
                self._check_cancelled(request)
                merged_pdf = workspace / "merged.pdf"
                progress("merging", 0, 1, "")
                page_count = assemble_pdf(
                    merged_pdf,
                    (
                        PdfSection("E-Mail", rendered_pdf, allow_separator=False),
                        *converted,
                    ),
                    document,
                    title=request.metadata.title,
                    separator_pages=request.metadata.separator_pages,
                    cancellation=request.cancellation,
                )
                progress("merging", 1, 1, "")
                progress("saving", 0, 1, "")
                output_path = store_pdf(
                    merged_pdf,
                    request.output_directory,
                    request.metadata.file_name,
                )
                progress("saving", 1, 1, "")
                return ArchiveResult(
                    output_path=output_path,
                    page_count=page_count,
                    included_attachments=tuple(
                        attachment.name for attachment in selected_attachments
                    ),
                    skipped_attachments=tuple(
                        attachment.name
                        for attachment in document.attachments
                        if attachment.index not in selected_indices
                    ),
                )
        finally:
            request.eml_path.unlink(missing_ok=True)

    @staticmethod
    def _check_cancelled(request: ArchiveRequest) -> None:
        """Raise the stable cancellation response at orchestration boundaries."""
        if request.cancellation.is_set():
            raise CancelledError

    @staticmethod
    def _validate_attachment_selection(request: ArchiveRequest, parsed_count: int) -> None:
        """Prevent review/native MIME-order drift from selecting a different attachment."""
        if parsed_count != request.metadata.attachment_count:
            raise HostError(
                "attachment_list_changed",
                "The attachment list changed after review. Reopen the archive dialog.",
            )
        indices = request.metadata.selected_attachment_indices
        if len(indices) != len(set(indices)) or any(
            index < 0 or index >= parsed_count for index in indices
        ):
            raise HostError(
                "invalid_attachment_selection",
                "The selected attachment list is invalid.",
            )
