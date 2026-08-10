"""Transfer tests cover ordering, duplication, absence, cancellation, and checksum failures."""

import base64
import hashlib
import tempfile
from pathlib import Path

import pytest

from paperless_mail_archiver.errors import HostError
from paperless_mail_archiver.transfer import TransferManager


def _manager_in(monkeypatch: pytest.MonkeyPatch, directory: Path) -> TransferManager:
    """Route transfer files into a test-owned directory for cleanup assertions."""
    original_mkstemp = tempfile.mkstemp
    monkeypatch.setattr(
        "paperless_mail_archiver.transfer.tempfile.mkstemp",
        lambda *, prefix, suffix: original_mkstemp(prefix=prefix, suffix=suffix, dir=directory),
    )
    return TransferManager()


def _start(
    manager: TransferManager, content: bytes, *, chunks: int = 1, checksum: str | None = None
) -> None:
    """Start one test job using a correct digest by default."""
    manager.start("job-1", len(content), chunks, checksum or hashlib.sha256(content).hexdigest())


def test_transfer_reassembles_and_verifies(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """An ordered stream is returned byte-for-byte only after verification."""
    content = b"Subject: test\r\n\r\nbody"
    manager = _manager_in(monkeypatch, tmp_path)
    _start(manager, content, chunks=2)
    manager.append("job-1", 0, base64.b64encode(content[:10]).decode("ascii"))
    manager.append("job-1", 1, base64.b64encode(content[10:]).decode("ascii"))

    result = manager.commit("job-1")
    assert result.read_bytes() == content
    result.unlink()


@pytest.mark.parametrize("index", [1, 2])
def test_out_of_order_or_duplicate_chunk_cleans_up(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    index: int,
) -> None:
    """Any non-next index invalidates the entire temporary transfer."""
    content = b"message"
    manager = _manager_in(monkeypatch, tmp_path)
    _start(manager, content, chunks=2)

    with pytest.raises(HostError, match="strict order"):
        manager.append("job-1", index, base64.b64encode(content).decode("ascii"))
    assert list(tmp_path.iterdir()) == []


def test_missing_chunk_cleans_up(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Commit rejects an incomplete stream and deletes its partial file."""
    content = b"message"
    manager = _manager_in(monkeypatch, tmp_path)
    _start(manager, content, chunks=2)
    manager.append("job-1", 0, base64.b64encode(content).decode("ascii"))

    with pytest.raises(HostError, match="missing"):
        manager.commit("job-1")
    assert list(tmp_path.iterdir()) == []


def test_checksum_failure_cleans_up(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A digest mismatch never exposes unverified EML data to the parser."""
    content = b"message"
    manager = _manager_in(monkeypatch, tmp_path)
    _start(manager, content, checksum="0" * 64)
    manager.append("job-1", 0, base64.b64encode(content).decode("ascii"))

    with pytest.raises(HostError, match="checksum"):
        manager.commit("job-1")
    assert list(tmp_path.iterdir()) == []


def test_cancellation_cleans_up(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Cancelling an active transfer removes its temporary EML immediately."""
    content = b"message"
    manager = _manager_in(monkeypatch, tmp_path)
    _start(manager, content)

    assert manager.cancel("job-1") is True
    assert list(tmp_path.iterdir()) == []
