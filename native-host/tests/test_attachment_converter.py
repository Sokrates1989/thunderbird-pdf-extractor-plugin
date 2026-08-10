"""Attachment converter tests cover redacted failures for unsafe selected input."""

from io import BytesIO
from pathlib import Path
from threading import Event

import pytest
from pypdf import PdfReader, PdfWriter

from paperless_mail_archiver.attachment_converter import AttachmentConverter
from paperless_mail_archiver.errors import HostError
from paperless_mail_archiver.models import AttachmentInfo
from paperless_mail_archiver.renderers import ReportLabMailRenderer
from tests.helpers import searchable_pdf_bytes


def encrypted_pdf_bytes() -> bytes:
    """Wrap the valid PDF fixture with a non-empty user password."""
    writer = PdfWriter()
    writer.append(BytesIO(searchable_pdf_bytes()))
    writer.encrypt("secret")
    output = BytesIO()
    writer.write(output)
    writer.close()
    return output.getvalue()


def empty_password_pdf_bytes() -> bytes:
    """Wrap the valid fixture in encryption that requires no user-supplied password."""
    writer = PdfWriter()
    writer.append(BytesIO(searchable_pdf_bytes("EMPTY PASSWORD PDF")))
    writer.encrypt("")
    output = BytesIO()
    writer.write(output)
    writer.close()
    return output.getvalue()


def test_empty_password_pdf_is_normalized_and_remains_searchable(tmp_path: Path) -> None:
    """Common owner-protected receipts merge after safe empty-password normalization."""
    payload = empty_password_pdf_bytes()
    attachment = AttachmentInfo(
        0,
        "owner-protected-receipt.pdf",
        "application/pdf",
        len(payload),
        payload,
    )
    converter = AttachmentConverter(ReportLabMailRenderer(), None)

    section = converter.convert(
        attachment,
        tmp_path,
        Event(),
        image_mode="placeholder",
    )

    reader = PdfReader(section.path)
    assert reader.is_encrypted is False
    assert "EMPTY PASSWORD PDF" in (reader.pages[0].extract_text() or "")


def test_selected_encrypted_pdf_names_the_failed_attachment(tmp_path: Path) -> None:
    """Encrypted attachments abort instead of producing a partial merged document."""
    attachment = AttachmentInfo(
        0,
        "protected-invoice.pdf",
        "application/pdf",
        len(encrypted_pdf_bytes()),
        encrypted_pdf_bytes(),
    )
    converter = AttachmentConverter(ReportLabMailRenderer(), None)

    with pytest.raises(HostError, match=r"protected-invoice\.pdf") as captured:
        converter.convert(
            attachment,
            tmp_path,
            Event(),
            image_mode="placeholder",
        )

    assert captured.value.code == "encrypted_attachment"
    assert list(tmp_path.iterdir()) == []


class _CompletedOfficeProcess:
    """Minimal successful Popen stand-in for command and profile inspection."""

    returncode = 0

    def poll(self) -> int:
        """Report immediate completion."""
        return 0


def test_office_conversion_uses_isolated_macro_hardened_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LibreOffice receives no shell and reads Very High security from profile/user."""
    observed: dict[str, object] = {}

    def fake_popen(command: list[str], **kwargs: object) -> _CompletedOfficeProcess:
        observed["command"] = command
        observed.update(kwargs)
        output_directory = Path(command[command.index("--outdir") + 1])
        (output_directory / "document.pdf").write_bytes(searchable_pdf_bytes("OFFICE OUTPUT"))
        return _CompletedOfficeProcess()

    monkeypatch.setattr(
        "paperless_mail_archiver.libreoffice_converter.subprocess.Popen",
        fake_popen,
    )
    attachment = AttachmentInfo(
        0,
        "report.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        4,
        b"docx",
    )
    converter = AttachmentConverter(ReportLabMailRenderer(), Path("soffice.exe"))

    section = converter.convert(
        attachment,
        tmp_path,
        Event(),
        image_mode="placeholder",
    )

    command = observed["command"]
    assert isinstance(command, list)
    assert "--headless" in command
    assert any(str(item).startswith("-env:UserInstallation=file:") for item in command)
    assert observed["shell"] is False
    profile = tmp_path / "office-0001" / "profile" / "user" / "registrymodifications.xcu"
    assert "MacroSecurityLevel" in profile.read_text(encoding="utf-8")
    assert "<value>3</value>" in profile.read_text(encoding="utf-8")
    assert section.path.is_file()
