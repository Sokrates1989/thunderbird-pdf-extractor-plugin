"""Isolated, macro-hardened local LibreOffice attachment conversion."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from threading import Event

from paperless_mail_archiver.errors import CancelledError, HostError
from paperless_mail_archiver.models import AttachmentInfo
from paperless_mail_archiver.pdf_assembler import validate_attachment_pdf

OFFICE_TIMEOUT_SECONDS = 120.0
PROCESS_POLL_SECONDS = 0.05

MACRO_SECURITY_PROFILE = """<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry">
  <item oor:path="/org.openoffice.Office.Common/Security/Scripting">
    <prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop>
  </item>
</oor:items>
"""


def convert_office_attachment(
    attachment: AttachmentInfo,
    target: Path,
    workspace: Path,
    cancellation: Event,
    executable: Path | None,
    sequence: int,
) -> None:
    """Run LibreOffice headlessly with macros disabled in an isolated profile."""
    if executable is None:
        raise HostError(
            "libreoffice_unavailable",
            f"{attachment.name}: LibreOffice is not installed.",
        )
    conversion = workspace / f"office-{sequence:04d}"
    input_directory = conversion / "input"
    output_directory = conversion / "output"
    profile_directory = conversion / "profile"
    input_directory.mkdir(parents=True)
    output_directory.mkdir()
    profile_user_directory = profile_directory / "user"
    profile_user_directory.mkdir(parents=True)
    suffix = Path(attachment.name).suffix.lower()
    source = input_directory / f"document{suffix}"
    source.write_bytes(attachment.data)
    (profile_user_directory / "registrymodifications.xcu").write_text(
        MACRO_SECURITY_PROFILE,
        encoding="utf-8",
    )
    command = [
        str(executable),
        "--headless",
        "--nologo",
        "--nodefault",
        "--nolockcheck",
        "--norestore",
        f"-env:UserInstallation={profile_directory.as_uri()}",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_directory),
        str(source),
    ]
    creation_flags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
    try:
        process = subprocess.Popen(  # noqa: S603 - Path is locally detected, never email-controlled.
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            creationflags=creation_flags,
        )
    except OSError as error:
        raise HostError(
            "libreoffice_failed",
            f"{attachment.name}: LibreOffice could not be started.",
        ) from error
    deadline = time.monotonic() + OFFICE_TIMEOUT_SECONDS
    while process.poll() is None:
        if cancellation.wait(PROCESS_POLL_SECONDS):
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
            raise HostError(
                "libreoffice_timeout",
                f"{attachment.name}: LibreOffice conversion timed out.",
            )
    converted = output_directory / "document.pdf"
    if process.returncode != 0 or not converted.is_file():
        raise HostError(
            "libreoffice_failed",
            f"{attachment.name}: LibreOffice could not convert this attachment.",
        )
    shutil.copyfile(converted, target)
    validate_attachment_pdf(target, attachment.name)
