"""Provide explicit Windows folder selection and opening behind the native boundary."""

from __future__ import annotations

import base64
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import cast

from paperless_mail_archiver.errors import HostError
from paperless_mail_archiver.output_store import validate_output_directory

FOLDER_PICKER_TIMEOUT_SECONDS = 600
MAX_PICKER_OUTPUT_CHARACTERS = 32_767

_FOLDER_PICKER_SCRIPT = r"""
Add-Type -AssemblyName System.Windows.Forms
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = [Environment]::GetEnvironmentVariable('TB_PDF_PICKER_TITLE')
$dialog.ShowNewFolderButton = $true
$initial = [Environment]::GetEnvironmentVariable('TB_PDF_INITIAL_DIRECTORY')
if (-not [string]::IsNullOrWhiteSpace($initial) -and [System.IO.Directory]::Exists($initial)) {
    $dialog.SelectedPath = $initial
}
try {
    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        [Console]::Write($dialog.SelectedPath)
    }
}
finally {
    $dialog.Dispose()
}
"""


def _powershell_executable() -> Path:
    """Resolve the inbox Windows PowerShell executable without relying on ``PATH``."""
    windows_root = Path(os.environ.get("WINDIR", "C:/Windows"))
    executable = windows_root / "System32/WindowsPowerShell/v1.0/powershell.exe"
    if not executable.is_file():
        raise HostError("folder_picker_unavailable", "Windows PowerShell is unavailable.")
    return executable


def choose_output_directory(initial_directory: Path | None, title: str) -> Path | None:
    """Show the Windows folder dialog and return a validated selection or cancellation."""
    if os.name != "nt":
        raise HostError("folder_picker_unavailable", "The folder picker requires Windows.")
    encoded_script = base64.b64encode(_FOLDER_PICKER_SCRIPT.encode("utf-16-le")).decode("ascii")
    environment = os.environ.copy()
    environment["TB_PDF_PICKER_TITLE"] = title
    environment["TB_PDF_INITIAL_DIRECTORY"] = (
        "" if initial_directory is None else str(initial_directory)
    )
    creation_flags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
    try:
        result = subprocess.run(  # noqa: S603 - Executable is a verified Windows system path.
            [
                str(_powershell_executable()),
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-STA",
                "-EncodedCommand",
                encoded_script,
            ],
            capture_output=True,
            check=False,
            creationflags=creation_flags,
            encoding="utf-8",
            env=environment,
            shell=False,
            timeout=FOLDER_PICKER_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise HostError("folder_picker_failed", "The folder picker could not be opened.") from error
    if result.returncode != 0:
        raise HostError("folder_picker_failed", "The folder picker did not complete successfully.")
    selected = result.stdout.strip()
    if not selected:
        return None
    if len(selected) > MAX_PICKER_OUTPUT_CHARACTERS:
        raise HostError("folder_picker_failed", "The selected folder path is too long.")
    return validate_output_directory(Path(selected))


def open_output_directory(directory: Path, opener: Callable[[str], object] | None = None) -> None:
    """Open one validated output folder in the user's default Windows file manager."""
    validated = validate_output_directory(directory)
    selected_opener = opener
    if selected_opener is None:
        startfile = getattr(os, "startfile", None)
        if not callable(startfile):
            raise HostError("open_directory_unavailable", "Opening folders requires Windows.")
        selected_opener = cast(Callable[[str], object], startfile)
    try:
        selected_opener(str(validated))
    except OSError as error:
        raise HostError(
            "open_directory_failed", "The output folder could not be opened."
        ) from error
