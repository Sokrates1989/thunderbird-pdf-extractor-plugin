"""macOS integration tests keep Finder and AppleScript calls bounded and testable."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from paperless_mail_archiver import macos_integration


def test_choose_output_directory_passes_arguments_without_shell_parsing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The picker receives title and initial folder as arguments and validates its result."""
    executable = tmp_path / "osascript"
    executable.touch()
    selected = tmp_path / "Selected folder"
    selected.mkdir()
    initial = tmp_path / "Initial folder"
    initial.mkdir()
    observed: list[list[str]] = []

    def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        observed.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=f"{selected}\n", stderr="")

    monkeypatch.setattr(macos_integration, "OSASCRIPT_EXECUTABLE", executable)

    result = macos_integration.choose_output_directory(initial, "Choose a folder", runner)

    assert result == selected.resolve()
    assert observed[0][0] == str(executable)
    assert observed[0][-2:] == ["Choose a folder", str(initial.resolve())]


def test_choose_output_directory_treats_empty_output_as_cancellation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A normal user cancellation returns no path instead of becoming a host error."""
    executable = tmp_path / "osascript"
    executable.touch()

    def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(macos_integration, "OSASCRIPT_EXECUTABLE", executable)

    assert macos_integration.choose_output_directory(None, "Choose", runner) is None


def test_open_output_directory_passes_validated_path_to_opener(tmp_path: Path) -> None:
    """The Finder boundary receives one resolved existing directory and nothing else."""
    opened: list[str] = []

    macos_integration.open_output_directory(tmp_path, opened.append)

    assert opened == [str(tmp_path.resolve())]
