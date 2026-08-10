"""Small RFC 822 fixtures generated with Python's standards-based email API."""

import base64
import struct
import zlib
from email.message import EmailMessage
from email.policy import SMTP
from io import BytesIO

from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas

VALID_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def sample_banner_png_bytes() -> bytes:
    """Create a dependency-free two-color PNG large enough for print inspection."""
    width = 320
    height = 160
    rows = bytearray()
    for row in range(height):
        color = bytes((0x1B, 0x6A, 0xB8)) if row < height // 2 else bytes((0xF2, 0xB7, 0x05))
        rows.extend(b"\x00")
        rows.extend(color * width)

    def chunk(kind: bytes, payload: bytes) -> bytes:
        """Frame one PNG chunk with its length and CRC."""
        checksum = zlib.crc32(kind + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(bytes(rows), level=9))
        + chunk(b"IEND", b"")
    )


def plain_email_bytes(*, body: str = "Bitte bis 20.08.2026 bezahlen.") -> bytes:
    """Return a German plain-text invoice-style email."""
    message = EmailMessage()
    message["Subject"] = "Rechnung August – Büromaterial"  # noqa: RUF001 - Unicode fixture.
    message["From"] = "Erika Muster <erika@example.test>"
    message["To"] = "Max Empfänger <max@example.test>"
    message["Date"] = "Mon, 10 Aug 2026 10:30:00 +0200"
    message["Message-ID"] = "<invoice-2026-08@example.test>"
    message.set_content(body, charset="utf-8")
    return message.as_bytes(policy=SMTP)


def alternative_email_bytes() -> bytes:
    """Return multipart/alternative content with intentionally distinct bodies."""
    message = EmailMessage()
    message["Subject"] = "Alternative"
    message["From"] = "sender@example.test"
    message["To"] = "recipient@example.test"
    message.set_content("PLAIN VERSION MUST NOT APPEAR")
    message.add_alternative(
        "<html><body><p>HTML version is selected.</p></body></html>",
        subtype="html",
    )
    return message.as_bytes(policy=SMTP)


def attachment_email_bytes() -> bytes:
    """Return one real PDF attachment and one inline tracking-style image."""
    message = EmailMessage()
    message["Subject"] = "Mit Anhang"
    message["From"] = "sender@example.test"
    message["To"] = "recipient@example.test"
    message.set_content("Fallback")
    message.add_alternative(
        '<p>Body<img src="cid:pixel@example.test" alt="Logo"></p>',
        subtype="html",
    )
    payload = message.get_payload()
    assert isinstance(payload, list)
    html_part = payload[1]
    assert isinstance(html_part, EmailMessage)
    html_part.add_related(
        VALID_PNG,
        maintype="image",
        subtype="png",
        cid="<pixel@example.test>",
        disposition="inline",
        filename="pixel.png",
    )
    message.add_attachment(
        b"%PDF-1.4\nplaceholder",
        maintype="application",
        subtype="pdf",
        filename="invoice.pdf",
    )
    return message.as_bytes(policy=SMTP)


def searchable_pdf_bytes(text: str = "ORIGINAL PDF ATTACHMENT") -> bytes:
    """Create a one-page searchable landscape PDF for merge tests."""
    output = BytesIO()
    document = canvas.Canvas(output, pagesize=landscape(letter))
    document.drawString(72, 400, text)
    document.linkURL("https://example.test/active-link", (72, 390, 300, 420), relative=0)
    document.showPage()
    document.save()
    return output.getvalue()


def slice_two_email_bytes() -> bytes:
    """Return supported and unsupported attachments in a known MIME order."""
    message = EmailMessage()
    message["Subject"] = "Slice 2 merge"
    message["From"] = "sender@example.test"
    message["To"] = "recipient@example.test"
    message.set_content("EMAIL BODY FIRST")
    message.add_attachment(
        searchable_pdf_bytes(),
        maintype="application",
        subtype="pdf",
        filename="01-original.pdf",
    )
    message.add_attachment(
        sample_banner_png_bytes(),
        maintype="image",
        subtype="png",
        filename="02-scan.png",
    )
    message.add_attachment(
        b"alpha,beta\n1,2\n",
        maintype="text",
        subtype="csv",
        filename="03-data.csv",
    )
    message.add_attachment(
        b"PK\x03\x04not-a-real-archive",
        maintype="application",
        subtype="zip",
        filename="04-archive.zip",
    )
    return message.as_bytes(policy=SMTP)


def nested_email_bytes() -> bytes:
    """Return one attached EML whose own supported attachment must be included recursively."""
    nested = EmailMessage()
    nested["Subject"] = "Nested message"
    nested["From"] = "nested@example.test"
    nested["To"] = "recipient@example.test"
    nested.set_content("NESTED EMAIL BODY")
    nested.add_attachment(
        b"NESTED TEXT ATTACHMENT",
        maintype="text",
        subtype="plain",
        filename="inside.txt",
    )

    outer = EmailMessage()
    outer["Subject"] = "Outer message"
    outer["From"] = "outer@example.test"
    outer["To"] = "recipient@example.test"
    outer.set_content("OUTER EMAIL BODY")
    outer.add_attachment(nested, filename="forwarded.eml")
    return outer.as_bytes(policy=SMTP)
