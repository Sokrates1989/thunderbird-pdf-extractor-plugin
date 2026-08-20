"""Dispatch desktop integration to the explicitly supported operating-system boundary."""

from __future__ import annotations

import platform
from pathlib import Path
from typing import Literal

from paperless_mail_archiver.errors import HostError

RuntimePlatform = Literal["macos", "other", "windows"]


def runtime_platform() -> RuntimePlatform:
    """Return the bounded platform token exposed through redacted diagnostics."""
    system_name = platform.system()
    if system_name == "Darwin":
        return "macos"
    if system_name == "Windows":
        return "windows"
    return "other"


def choose_output_directory(initial_directory: Path | None, title: str) -> Path | None:
    """Show the supported platform's native folder picker."""
    if platform.system() == "Darwin":
        from paperless_mail_archiver.macos_integration import (
            choose_output_directory as choose_macos,
        )

        return choose_macos(initial_directory, title)
    if platform.system() == "Windows":
        from paperless_mail_archiver.windows_integration import (
            choose_output_directory as choose_windows,
        )

        return choose_windows(initial_directory, title)
    raise HostError("folder_picker_unavailable", "The folder picker is unavailable.")


def open_output_directory(directory: Path) -> None:
    """Open a validated directory using the supported platform's file manager."""
    if platform.system() == "Darwin":
        from paperless_mail_archiver.macos_integration import (
            open_output_directory as open_directory,
        )

        open_directory(directory)
        return
    if platform.system() == "Windows":
        from paperless_mail_archiver.windows_integration import (
            open_output_directory as open_directory,
        )

        open_directory(directory)
        return
    raise HostError("open_directory_unavailable", "Opening folders is unavailable.")
