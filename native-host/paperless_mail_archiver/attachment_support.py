"""Attachment conversion classification and optional LibreOffice discovery."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from paperless_mail_archiver.models import AttachmentInfo

AttachmentKind = Literal["pdf", "image", "text", "html", "eml", "office", "unsupported"]

IMAGE_EXTENSIONS = frozenset({".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"})
IMAGE_MIME_TYPES = frozenset(
    {
        "image/bmp",
        "image/jpeg",
        "image/png",
        "image/tiff",
        "image/webp",
        "image/x-ms-bmp",
    }
)
TEXT_EXTENSIONS = frozenset({".csv", ".txt"})
TEXT_MIME_TYPES = frozenset({"application/csv", "text/csv", "text/plain"})
HTML_EXTENSIONS = frozenset({".htm", ".html"})
HTML_MIME_TYPES = frozenset({"application/xhtml+xml", "text/html"})
OFFICE_EXTENSIONS = frozenset({".docx", ".odp", ".ods", ".odt", ".pptx", ".xlsx"})


@dataclass(frozen=True, slots=True)
class AttachmentSupport:
    """State whether the local companion can convert one attachment."""

    kind: AttachmentKind
    supported: bool
    detail: str


def attachment_kind(name: str, content_type: str) -> AttachmentKind:
    """Classify by reviewed MIME type and extension without trusting either exclusively."""
    suffix = Path(name).suffix.lower()
    mime = content_type.lower().partition(";")[0].strip()
    if mime == "application/pdf" or suffix == ".pdf":
        return "pdf"
    if mime in IMAGE_MIME_TYPES or suffix in IMAGE_EXTENSIONS:
        return "image"
    if mime in TEXT_MIME_TYPES or suffix in TEXT_EXTENSIONS:
        return "text"
    if mime in HTML_MIME_TYPES or suffix in HTML_EXTENSIONS:
        return "html"
    if mime == "message/rfc822" or suffix == ".eml":
        return "eml"
    if suffix in OFFICE_EXTENSIONS:
        return "office"
    return "unsupported"


def attachment_support(
    attachment: AttachmentInfo,
    libreoffice_executable: Path | None,
) -> AttachmentSupport:
    """Return a stable preflight result used by orchestration and tests."""
    kind = attachment_kind(attachment.name, attachment.content_type)
    if kind == "office" and libreoffice_executable is None:
        return AttachmentSupport(kind, False, "LibreOffice is not installed.")
    if kind == "unsupported":
        return AttachmentSupport(kind, False, "This file type is not supported.")
    return AttachmentSupport(kind, True, "Included in the merged PDF.")


def detect_libreoffice() -> Path | None:
    """Find a local LibreOffice executable without downloading or starting software."""
    candidates: list[Path] = []
    for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        root = os.environ.get(variable)
        if root:
            candidates.append(Path(root) / "LibreOffice/program/soffice.exe")
    for executable_name in ("soffice", "libreoffice"):
        resolved = shutil.which(executable_name)
        if resolved:
            candidates.append(Path(resolved))
    return next((candidate.resolve() for candidate in candidates if candidate.is_file()), None)
