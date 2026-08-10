"""Text-preserving Chromium renderer with a deterministic ReportLab fallback."""

from __future__ import annotations

import html
import os
import shutil
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from pathlib import Path
from threading import Event
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer

from paperless_mail_archiver.errors import CancelledError, HostError
from paperless_mail_archiver.html_sanitizer import html_to_text, sanitize_html
from paperless_mail_archiver.image_resources import ImageSourceResolver
from paperless_mail_archiver.models import ImageMode, MailDocument

CHROMIUM_TIMEOUT_SECONDS = 60.0
CHROMIUM_POLL_SECONDS = 0.05
MINIMUM_PDF_BYTES = 100


class RendererUnavailableError(HostError):
    """Indicate that Chromium rendering cannot be used on this computer."""

    def __init__(self, message: str) -> None:
        """Initialize a renderer-specific recoverable error."""
        super().__init__("chromium_unavailable", message)


class MailRenderer(ABC):
    """Render one normalized email as a searchable PDF."""

    @abstractmethod
    def render(
        self,
        document: MailDocument,
        target: Path,
        cancellation: Event,
        *,
        include_body: bool,
        image_mode: ImageMode,
    ) -> None:
        """Render the document into ``target`` or raise a coded host error."""


def _metadata_rows(document: MailDocument) -> list[tuple[str, str]]:
    """Build the non-empty metadata rows shown at the start of the PDF."""
    rows = [
        ("From", document.sender),
        ("To", document.recipients),
        ("CC", document.cc),
        ("Sent", document.sent_date),
        ("Message-ID", document.message_id),
    ]
    return [(label, value) for label, value in rows if value]


def _body_fragment(
    document: MailDocument,
    *,
    include_body: bool,
    image_resolver: ImageSourceResolver | None = None,
) -> str:
    """Return only sanitized HTML or escaped plain text for the email body."""
    if not include_body:
        return '<p class="muted">Email body was excluded by the user.</p>'
    if document.body_kind == "html":
        return sanitize_html(document.body, image_resolver.resolve if image_resolver else None)
    escaped = html.escape(document.body).replace("\r\n", "\n").replace("\r", "\n")
    return f'<div class="plain">{escaped.replace(chr(10), "<br>")}</div>'


def build_safe_html(
    document: MailDocument,
    *,
    include_body: bool,
    image_resolver: ImageSourceResolver | None = None,
) -> str:
    """Create a complete CSP-constrained local document for print rendering."""
    metadata = "".join(
        f"<dt>{html.escape(label)}</dt><dd>{html.escape(value)}</dd>"
        for label, value in _metadata_rows(document)
    )
    decisions = {decision.index: decision for decision in document.attachment_decisions}
    attachments = "".join(
        "<li>"
        f"{html.escape(attachment.name)} "
        f"<span>({html.escape(attachment.content_type)}, {attachment.size} bytes) - "
        f"{html.escape(decisions[attachment.index].detail if attachment.index in decisions else 'Skipped.')}</span></li>"
        for attachment in document.attachments
    )
    if not attachments:
        attachments = "<li>No attachments detected.</li>"
    body = _body_fragment(
        document,
        include_body=include_body,
        image_resolver=image_resolver,
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src 'none'; connect-src 'none'; frame-src 'none'">
<style>
@page {{ size: A4; margin: 18mm; }}
body {{ color: #1b1b1b; font: 11pt/1.45 Arial, sans-serif; overflow-wrap: anywhere; }}
h1 {{ font-size: 18pt; line-height: 1.2; margin: 0 0 7mm; }}
h2 {{ border-bottom: 1px solid #bbb; font-size: 12pt; margin-top: 8mm; padding-bottom: 2mm; }}
dl {{ display: grid; grid-template-columns: max-content 1fr; gap: 1mm 4mm; margin: 0; }}
dt {{ color: #555; font-weight: bold; }} dd {{ margin: 0; }}
table {{ border-collapse: collapse; max-width: 100%; }} td, th {{ border: 1px solid #bbb; padding: 2mm; }}
.plain {{ white-space: normal; }} .muted, li span {{ color: #666; font-size: 9pt; }}
img {{ display: block; height: auto; margin: 2mm auto; max-width: 100%; page-break-inside: avoid; }}
.image-placeholder {{ background: #f2f2f2; border: 1px solid #ccc; color: #666; display: inline-block; font-size: 9pt; margin: 1mm 0; padding: 1.5mm 2mm; }}
a.image-link .image-placeholder {{ color: #0645ad; text-decoration: underline; }}
</style></head><body>
<h1>{html.escape(document.subject)}</h1><dl>{metadata}</dl>
<h2>Email</h2><section>{body}</section>
<h2>Attachments</h2><ul>{attachments}</ul>
</body></html>"""


def detect_chromium() -> Path | None:
    """Find a supported browser using stable Windows locations and PATH."""
    candidates: list[Path] = []
    program_files_x86 = os.environ.get("PROGRAMFILES(X86)")
    program_files = os.environ.get("PROGRAMFILES")
    local_app_data = os.environ.get("LOCALAPPDATA")
    if program_files_x86:
        candidates.extend(
            [
                Path(program_files_x86) / "Microsoft/Edge/Application/msedge.exe",
                Path(program_files_x86) / "Google/Chrome/Application/chrome.exe",
            ]
        )
    if program_files:
        candidates.extend(
            [
                Path(program_files) / "Microsoft/Edge/Application/msedge.exe",
                Path(program_files) / "Google/Chrome/Application/chrome.exe",
            ]
        )
    if local_app_data:
        candidates.extend(
            [
                Path(local_app_data) / "Microsoft/Edge/Application/msedge.exe",
                Path(local_app_data) / "Google/Chrome/Application/chrome.exe",
            ]
        )
    for executable_name in ("msedge", "chrome", "chromium", "chromium-browser"):
        resolved = shutil.which(executable_name)
        if resolved:
            candidates.append(Path(resolved))
    return next((candidate for candidate in candidates if candidate.is_file()), None)


class ChromiumMailRenderer(MailRenderer):
    """Print a CSP-constrained local HTML document with Edge, Chrome, or Chromium."""

    def __init__(self, executable: Path | None = None) -> None:
        """Use a caller-provided browser or detect an installed supported browser."""
        self._executable = executable or detect_chromium()

    def render(
        self,
        document: MailDocument,
        target: Path,
        cancellation: Event,
        *,
        include_body: bool,
        image_mode: ImageMode,
    ) -> None:
        """Render without network dependencies and cooperatively terminate on cancellation."""
        if self._executable is None:
            raise RendererUnavailableError("No supported Chromium browser was found.")
        if cancellation.is_set():
            raise CancelledError
        with tempfile.TemporaryDirectory(prefix="tb-render-") as temporary_directory:
            workspace = Path(temporary_directory)
            source = workspace / "email.html"
            profile = workspace / "browser-profile"
            image_resolver = (
                ImageSourceResolver(document, cancellation) if image_mode == "embed" else None
            )
            source.write_text(
                build_safe_html(
                    document,
                    include_body=include_body,
                    image_resolver=image_resolver,
                ),
                encoding="utf-8",
            )
            command = [
                str(self._executable),
                "--headless=new",
                "--disable-background-networking",
                "--disable-component-update",
                "--disable-default-apps",
                "--disable-extensions",
                "--disable-features=OptimizationHints,MediaRouter",
                "--disable-gpu",
                "--disable-sync",
                "--metrics-recording-only",
                "--no-default-browser-check",
                "--no-first-run",
                "--no-pdf-header-footer",
                f"--user-data-dir={profile}",
                f"--print-to-pdf={target}",
                source.as_uri(),
            ]
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            try:
                process = subprocess.Popen(  # noqa: S603 - Executable is a verified local browser path.
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    shell=False,
                    creationflags=creation_flags,
                )
            except OSError as error:
                raise RendererUnavailableError(
                    "The installed browser could not be started."
                ) from error
            deadline = time.monotonic() + CHROMIUM_TIMEOUT_SECONDS
            while process.poll() is None:
                if cancellation.wait(CHROMIUM_POLL_SECONDS):
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                    raise CancelledError
                if time.monotonic() >= deadline:
                    process.kill()
                    process.wait(timeout=5)
                    raise RendererUnavailableError("Chromium PDF rendering timed out.")
            if (
                process.returncode != 0
                or not target.is_file()
                or target.stat().st_size < MINIMUM_PDF_BYTES
            ):
                target.unlink(missing_ok=True)
                raise RendererUnavailableError("Chromium did not produce a valid PDF file.")


def register_unicode_font() -> str:
    """Register an available local Unicode font for deterministic fallback output."""
    font_name = "ArchiveUnicode"
    if font_name in pdfmetrics.getRegisteredFontNames():
        return font_name
    candidates = (
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/arial.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    )
    for candidate in candidates:
        if candidate.is_file():
            pdfmetrics.registerFont(TTFont(font_name, str(candidate)))
            return font_name
    return "Helvetica"


class ReportLabMailRenderer(MailRenderer):
    """Create a normalized searchable PDF without requiring an installed browser."""

    def render(
        self,
        document: MailDocument,
        target: Path,
        cancellation: Event,
        *,
        include_body: bool,
        image_mode: ImageMode,
    ) -> None:
        """Render decoded metadata, body text, and explicit attachment decisions."""
        if cancellation.is_set():
            raise CancelledError
        font_name = register_unicode_font()
        styles = getSampleStyleSheet()
        normal = ParagraphStyle(
            "ArchiveNormal",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=10,
            leading=14,
            alignment=TA_LEFT,
            spaceAfter=3 * mm,
        )
        heading = ParagraphStyle(
            "ArchiveHeading",
            parent=styles["Heading2"],
            fontName=font_name,
            fontSize=13,
            leading=16,
            spaceBefore=5 * mm,
            spaceAfter=2 * mm,
        )
        title_style = ParagraphStyle(
            "ArchiveTitle",
            parent=styles["Title"],
            fontName=font_name,
            fontSize=18,
            leading=22,
            alignment=TA_LEFT,
        )
        story: list[Flowable] = [
            Paragraph(xml_escape(document.subject), title_style),
            Spacer(1, 4 * mm),
        ]
        for label, value in _metadata_rows(document):
            story.append(Paragraph(f"<b>{xml_escape(label)}:</b> {xml_escape(value)}", normal))
        story.append(Paragraph("Email", heading))
        if include_body:
            body = sanitize_html(document.body) if document.body_kind == "html" else document.body
            readable = html_to_text(body) if document.body_kind == "html" else body
            paragraphs = [
                line.strip() for line in readable.replace("\r", "").split("\n") if line.strip()
            ]
            story.extend(Paragraph(xml_escape(line), normal) for line in paragraphs)
        else:
            story.append(Paragraph("Email body was excluded by the user.", normal))
        story.append(Paragraph("Attachments", heading))
        if document.attachments:
            decisions = {decision.index: decision for decision in document.attachment_decisions}
            for attachment in document.attachments:
                detail = (
                    decisions[attachment.index].detail
                    if attachment.index in decisions
                    else "Skipped."
                )
                description = (
                    f"• {attachment.name} ({attachment.content_type}, {attachment.size} bytes) - "
                    f"{detail}"
                )
                story.append(Paragraph(xml_escape(description), normal))
        else:
            story.append(Paragraph("No attachments detected.", normal))
        pdf = SimpleDocTemplate(
            str(target),
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title=document.subject,
            author=document.sender,
        )
        pdf.build(story)


class FallbackMailRenderer(MailRenderer):
    """Try high-fidelity local Chromium, then use normalized ReportLab output."""

    def __init__(self, primary: MailRenderer, fallback: MailRenderer) -> None:
        """Store explicit renderers to keep fallback behavior testable."""
        self._primary = primary
        self._fallback = fallback

    def render(
        self,
        document: MailDocument,
        target: Path,
        cancellation: Event,
        *,
        include_body: bool,
        image_mode: ImageMode,
    ) -> None:
        """Fallback only for browser availability failures, never cancellation."""
        try:
            self._primary.render(
                document,
                target,
                cancellation,
                include_body=include_body,
                image_mode=image_mode,
            )
        except RendererUnavailableError:
            target.unlink(missing_ok=True)
            self._fallback.render(
                document,
                target,
                cancellation,
                include_body=include_body,
                image_mode=image_mode,
            )
