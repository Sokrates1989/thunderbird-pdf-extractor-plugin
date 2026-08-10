"""Typed models shared by MIME parsing, rendering, and orchestration."""

from dataclasses import dataclass, field
from pathlib import Path
from threading import Event
from typing import Literal

ImageMode = Literal["placeholder", "embed"]
AttachmentDecisionStatus = Literal["included", "skipped"]


@dataclass(frozen=True, slots=True)
class AttachmentInfo:
    """Describe one real MIME attachment in its original order."""

    index: int
    name: str
    content_type: str
    size: int
    data: bytes = field(repr=False)
    charset: str = ""


@dataclass(frozen=True, slots=True)
class AttachmentDecision:
    """Record whether one attachment is merged and disclose the reason in the email PDF."""

    index: int
    status: AttachmentDecisionStatus
    detail: str


@dataclass(frozen=True, slots=True)
class InlineImage:
    """Hold one MIME image that HTML may reference without treating it as an attachment."""

    content_id: str
    content_location: str
    content_type: str
    data: bytes


@dataclass(frozen=True, slots=True)
class MailDocument:
    """Normalized, decoded email content that is safe to pass to renderers."""

    subject: str
    sender: str
    recipients: str
    cc: str
    sent_date: str
    message_id: str
    body: str
    body_kind: Literal["html", "plain"]
    attachments: tuple[AttachmentInfo, ...]
    inline_images: tuple[InlineImage, ...] = ()
    attachment_decisions: tuple[AttachmentDecision, ...] = ()


@dataclass(frozen=True, slots=True)
class ArchiveMetadata:
    """User-editable output choices supplied by the trusted extension UI."""

    title: str
    file_name: str
    include_body: bool
    attachment_count: int
    image_mode: ImageMode = "placeholder"
    selected_attachment_indices: tuple[int, ...] = ()
    separator_pages: bool = False


@dataclass(frozen=True, slots=True)
class ArchiveRequest:
    """Verified EML input and settings for one PDF job."""

    eml_path: Path
    metadata: ArchiveMetadata
    output_directory: Path
    cancellation: Event


@dataclass(frozen=True, slots=True)
class ArchiveResult:
    """Small result returned to the extension after local persistence."""

    output_path: Path
    page_count: int
    included_attachments: tuple[str, ...] = ()
    skipped_attachments: tuple[str, ...] = ()
