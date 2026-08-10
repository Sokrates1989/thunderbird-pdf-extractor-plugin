"""Safe RFC 822 parsing and single-body selection using Python's email package."""

from __future__ import annotations

import re
from email import policy
from email.message import EmailMessage, Message
from email.parser import BytesParser
from typing import Literal

from paperless_mail_archiver.errors import HostError
from paperless_mail_archiver.models import AttachmentInfo, InlineImage, MailDocument

MAX_DECODED_BODY_CHARACTERS = 5_000_000
MAX_ATTACHMENT_COUNT = 500
MAX_TOTAL_ATTACHMENT_BYTES = 50 * 1024 * 1024
MAX_ATTACHMENT_NAME_CHARACTERS = 240


def _header(message: Message, name: str) -> str:
    """Return a policy-decoded header without exposing parser objects downstream."""
    value = message.get(name)
    return "" if value is None else str(value)


def _decoded_text(part: Message) -> str:
    """Decode a text MIME part with replacement for malformed declared charsets."""
    payload = part.get_payload(decode=True)
    if isinstance(payload, bytes):
        charset = part.get_content_charset() or "utf-8"
        try:
            decoded = payload.decode(charset, errors="replace")
        except LookupError:
            decoded = payload.decode("utf-8", errors="replace")
    else:
        raw_payload = part.get_payload()
        decoded = raw_payload if isinstance(raw_payload, str) else ""
    if len(decoded) > MAX_DECODED_BODY_CHARACTERS:
        raise HostError("body_too_large", "The decoded email body exceeds the safe limit.")
    return decoded


def _body_part(message: EmailMessage) -> tuple[str, Literal["html", "plain"]]:
    """Prefer one HTML alternative and otherwise return one plain-text body."""
    preferred = message.get_body(preferencelist=("html", "plain"))
    if preferred is not None:
        subtype = preferred.get_content_subtype()
        return _decoded_text(preferred), "html" if subtype == "html" else "plain"

    for part in _mime_parts(message):
        if part.get_content_maintype() == "text" and part.get_content_disposition() != "attachment":
            subtype = part.get_content_subtype()
            return _decoded_text(part), "html" if subtype == "html" else "plain"
    return "", "plain"


def _mime_parts(message: Message) -> tuple[Message, ...]:
    """Walk MIME children without descending into attached RFC 822 messages."""
    result: list[Message] = []
    payload = message.get_payload()
    if not isinstance(payload, list):
        return ()
    for part in payload:
        if not isinstance(part, Message):
            continue
        result.append(part)
        if part.get_content_type().lower() != "message/rfc822":
            result.extend(_mime_parts(part))
    return tuple(result)


def _safe_attachment_name(filename: str | None, index: int) -> str:
    """Reduce an untrusted MIME filename to a bounded display-only basename."""
    candidate = re.split(r"[/\\\\]", filename or "")[-1]
    candidate = "".join(character for character in candidate if ord(character) >= 32).strip()
    if not candidate:
        candidate = f"attachment-{index + 1}"
    return candidate[:MAX_ATTACHMENT_NAME_CHARACTERS]


def _attachment_bytes(part: Message) -> bytes:
    """Decode a leaf payload, including the special message/rfc822 representation."""
    if part.get_content_type().lower() == "message/rfc822":
        nested = part.get_payload()
        if isinstance(nested, list) and nested and isinstance(nested[0], Message):
            return nested[0].as_bytes(policy=policy.default)
    payload = part.get_payload(decode=True)
    return payload if isinstance(payload, bytes) else b""


def _attachments(message: EmailMessage) -> tuple[AttachmentInfo, ...]:
    """List real non-inline attachments in original MIME traversal order."""
    attachments: list[AttachmentInfo] = []
    total_size = 0
    for part in _mime_parts(message):
        if part.is_multipart() and part.get_content_type().lower() != "message/rfc822":
            continue
        disposition = part.get_content_disposition()
        filename = part.get_filename()
        is_attachment = disposition == "attachment" or (
            filename is not None and disposition != "inline"
        )
        if not is_attachment:
            continue
        if len(attachments) >= MAX_ATTACHMENT_COUNT:
            raise HostError("too_many_attachments", "The email contains too many attachments.")
        payload = _attachment_bytes(part)
        size = len(payload)
        total_size += size
        if total_size > MAX_TOTAL_ATTACHMENT_BYTES:
            raise HostError(
                "attachments_too_large",
                "The decoded attachments exceed the safe total-size limit.",
            )
        index = len(attachments)
        attachments.append(
            AttachmentInfo(
                index=index,
                name=_safe_attachment_name(filename, index),
                content_type=part.get_content_type().lower(),
                size=size,
                data=payload,
                charset=part.get_content_charset() or "",
            )
        )
    return tuple(attachments)


def _inline_images(message: EmailMessage) -> tuple[InlineImage, ...]:
    """Collect non-attachment MIME images addressable by Content-ID or location."""
    images: list[InlineImage] = []
    for part in _mime_parts(message):
        if part.is_multipart() or part.get_content_maintype() != "image":
            continue
        if part.get_content_disposition() == "attachment":
            continue
        content_id = _header(part, "content-id").strip().strip("<>").lower()
        content_location = _header(part, "content-location").strip()
        if not content_id and not content_location:
            continue
        payload = part.get_payload(decode=True)
        if not isinstance(payload, bytes):
            continue
        images.append(
            InlineImage(
                content_id=content_id,
                content_location=content_location,
                content_type=part.get_content_type().lower(),
                data=payload,
            )
        )
    return tuple(images)


def parse_email(raw_message: bytes) -> MailDocument:
    """Parse untrusted EML bytes into one normalized document model."""
    try:
        parsed = BytesParser(policy=policy.default).parsebytes(raw_message)
    except (ValueError, TypeError) as error:
        raise HostError("invalid_eml", "The raw email could not be parsed.") from error
    if not isinstance(parsed, EmailMessage):
        raise HostError("invalid_eml", "The email parser returned an unsupported message type.")
    body, body_kind = _body_part(parsed)
    return MailDocument(
        subject=_header(parsed, "subject") or "E-Mail",
        sender=_header(parsed, "from"),
        recipients=_header(parsed, "to"),
        cc=_header(parsed, "cc"),
        sent_date=_header(parsed, "date"),
        message_id=_header(parsed, "message-id"),
        body=body,
        body_kind=body_kind,
        attachments=_attachments(parsed),
        inline_images=_inline_images(parsed),
    )
