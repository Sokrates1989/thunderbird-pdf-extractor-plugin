"""Windows integration tests keep folder opening scoped to validated directories."""

from pathlib import Path

from paperless_mail_archiver.windows_integration import open_output_directory


def test_open_output_directory_passes_validated_path_to_opener(tmp_path: Path) -> None:
    """The shell opener receives one resolved existing directory and nothing else."""
    opened: list[str] = []

    open_output_directory(tmp_path, opened.append)

    assert opened == [str(tmp_path.resolve())]
