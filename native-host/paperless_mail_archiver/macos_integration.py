"""Provide explicit macOS folder selection and Finder opening behind the native boundary."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

from paperless_mail_archiver.errors import HostError
from paperless_mail_archiver.output_store import validate_output_directory

FOLDER_PICKER_TIMEOUT_SECONDS = 600
MAX_PICKER_OUTPUT_CHARACTERS = 32_767
OSASCRIPT_EXECUTABLE = Path("/usr/bin/osascript")
OPEN_EXECUTABLE = Path("/usr/bin/open")

_FOLDER_PICKER_SCRIPT = """
on run argv
    set promptText to item 1 of argv
    set initialPath to item 2 of argv
    try
        if initialPath is "" then
            set chosenFolder to choose folder with prompt promptText
        else
            set chosenFolder to choose folder with prompt promptText default location POSIX file initialPath
        end if
        return POSIX path of chosenFolder
    on error number -128
        return ""
    end try
end run
"""

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def choose_output_directory(
    initial_directory: Path | None,
    title: str,
    runner: CommandRunner = subprocess.run,
) -> Path | None:
    """Show the macOS folder dialog and return a validated selection or cancellation."""
    if not OSASCRIPT_EXECUTABLE.is_file():
        raise HostError("folder_picker_unavailable", "The macOS folder picker is unavailable.")
    usable_initial = (
        initial_directory.resolve()
        if initial_directory is not None and initial_directory.is_dir()
        else ""
    )
    try:
        result = runner(
            [
                str(OSASCRIPT_EXECUTABLE),
                "-e",
                _FOLDER_PICKER_SCRIPT,
                "--",
                title,
                str(usable_initial),
            ],
            capture_output=True,
            check=False,
            encoding="utf-8",
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


def open_output_directory(
    directory: Path,
    opener: Callable[[str], object] | None = None,
) -> None:
    """Open one validated output folder in Finder."""
    validated = validate_output_directory(directory)
    if opener is not None:
        try:
            opener(str(validated))
        except OSError as error:
            raise HostError(
                "open_directory_failed", "The output folder could not be opened."
            ) from error
        return
    if not OPEN_EXECUTABLE.is_file():
        raise HostError("open_directory_unavailable", "Finder integration is unavailable.")
    try:
        result = subprocess.run(  # noqa: S603 - Executable is a fixed macOS system path.
            [str(OPEN_EXECUTABLE), str(validated)],
            capture_output=True,
            check=False,
            shell=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise HostError(
            "open_directory_failed", "The output folder could not be opened."
        ) from error
    if result.returncode != 0:
        raise HostError("open_directory_failed", "The output folder could not be opened.")
