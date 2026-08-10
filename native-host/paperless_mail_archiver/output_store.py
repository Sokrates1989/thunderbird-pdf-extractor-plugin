"""Validated, collision-free local PDF persistence for Windows output folders."""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path

from paperless_mail_archiver.errors import HostError

INVALID_WINDOWS_CHARACTERS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
RESERVED_WINDOWS_NAMES = re.compile(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?$", re.IGNORECASE)
MAX_FILE_NAME_LENGTH = 220
MAX_COLLISION_ATTEMPTS = 1000


def sanitize_pdf_file_name(file_name: str) -> str:
    """Return a bounded Windows-safe basename that cannot traverse directories."""
    sanitized = INVALID_WINDOWS_CHARACTERS.sub("_", file_name).strip().rstrip(". ")
    if not sanitized.lower().endswith(".pdf"):
        sanitized = f"{sanitized}.pdf"
    stem = Path(sanitized).stem or "E-Mail"
    if RESERVED_WINDOWS_NAMES.fullmatch(stem):
        stem = f"_{stem}"
    maximum_stem = MAX_FILE_NAME_LENGTH - len(".pdf")
    return f"{stem[:maximum_stem].rstrip('. ')}.pdf"


def validate_output_directory(output_directory: Path) -> Path:
    """Require an existing absolute directory without creating user-selected paths."""
    if not output_directory.is_absolute():
        raise HostError("output_directory_not_absolute", "The output directory must be absolute.")
    try:
        resolved = output_directory.resolve(strict=True)
    except OSError as error:
        raise HostError(
            "output_directory_missing", "The output directory does not exist."
        ) from error
    if not resolved.is_dir():
        raise HostError("output_directory_invalid", "The output path is not a directory.")
    return resolved


def test_output_directory_writable(output_directory: Path) -> None:
    """Create and remove an empty probe without retaining user data."""
    directory = validate_output_directory(output_directory)
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".thunderbird-probe-", delete=True):
            pass
    except OSError as error:
        raise HostError(
            "output_directory_not_writable", "The output directory is not writable."
        ) from error


def _candidate(directory: Path, safe_name: str, attempt: int) -> Path:
    """Build the original filename or a deterministic numbered collision variant."""
    original = Path(safe_name)
    if attempt == 0:
        return directory / original.name
    return directory / f"{original.stem} ({attempt + 1}){original.suffix}"


def store_pdf(source: Path, output_directory: Path, file_name: str) -> Path:
    """Copy then atomically link a complete PDF without overwriting existing files."""
    directory = validate_output_directory(output_directory)
    safe_name = sanitize_pdf_file_name(file_name)
    staging_descriptor, staging_name = tempfile.mkstemp(
        dir=directory,
        prefix=".thunderbird-mail-",
        suffix=".pdf",
    )
    staging = Path(staging_name)
    try:
        with os.fdopen(staging_descriptor, "wb") as destination, source.open("rb") as origin:
            shutil.copyfileobj(origin, destination)
            destination.flush()
            os.fsync(destination.fileno())
        for attempt in range(MAX_COLLISION_ATTEMPTS):
            destination_path = _candidate(directory, safe_name, attempt)
            try:
                os.link(staging, destination_path)
            except FileExistsError:
                continue
            except OSError as error:
                if os.name != "nt":
                    raise HostError(
                        "output_write_failed",
                        "The PDF could not be saved in the output folder.",
                    ) from error
                try:
                    # Windows rename is atomic and refuses to replace an existing target.
                    os.rename(staging, destination_path)
                except FileExistsError:
                    continue
                except OSError as rename_error:
                    raise HostError(
                        "output_write_failed",
                        "The PDF could not be saved in the output folder.",
                    ) from rename_error
                return destination_path
            staging.unlink()
            return destination_path
        raise HostError("too_many_collisions", "No unused output filename could be allocated.")
    except OSError as error:
        raise HostError(
            "output_write_failed", "The PDF could not be saved in the output folder."
        ) from error
    finally:
        staging.unlink(missing_ok=True)
