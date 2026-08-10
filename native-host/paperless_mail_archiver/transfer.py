"""Ordered, bounded, checksummed reassembly of Base64 EML chunks."""

from __future__ import annotations

import base64
import binascii
import hashlib
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, Protocol

from paperless_mail_archiver.errors import HostError

MAX_RAW_MESSAGE_BYTES = 50 * 1024 * 1024
MAX_RAW_CHUNK_BYTES = 512 * 1024
MAX_CHUNKS = 100
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class _HashDigest(Protocol):
    """Expose only the incremental SHA-256 operations used by transfers."""

    def update(self, data: bytes) -> None:
        """Add bytes to the digest."""

    def hexdigest(self) -> str:
        """Return the lower-case hexadecimal digest."""


@dataclass(slots=True)
class _TransferSession:
    """Mutable state for exactly one ordered incoming EML stream."""

    path: Path
    stream: BinaryIO
    total_bytes: int
    chunk_count: int
    expected_sha256: str
    next_index: int = 0
    received_bytes: int = 0
    digest: _HashDigest = field(default_factory=hashlib.sha256)


class TransferManager:
    """Own temporary EML files until verification or cancellation completes."""

    def __init__(self) -> None:
        """Initialize an empty job registry."""
        self._sessions: dict[str, _TransferSession] = {}

    def start(self, job_id: str, total_bytes: int, chunk_count: int, sha256: str) -> None:
        """Start a unique bounded transfer and allocate its restricted temporary file."""
        if job_id in self._sessions:
            raise HostError("duplicate_job", "A transfer with this job ID already exists.")
        if not 0 < total_bytes <= MAX_RAW_MESSAGE_BYTES:
            raise HostError("message_too_large", "The raw email size is outside the allowed range.")
        if not 0 < chunk_count <= MAX_CHUNKS:
            raise HostError(
                "invalid_chunk_count", "The EML chunk count is outside the allowed range."
            )
        if SHA256_PATTERN.fullmatch(sha256) is None:
            raise HostError("invalid_checksum", "The EML checksum has an invalid format.")

        descriptor, temporary_name = tempfile.mkstemp(prefix="tb-mail-", suffix=".eml")
        temporary = os.fdopen(descriptor, "wb")
        path = Path(temporary_name)
        path.chmod(0o600)
        self._sessions[job_id] = _TransferSession(
            path=path,
            stream=temporary,
            total_bytes=total_bytes,
            chunk_count=chunk_count,
            expected_sha256=sha256,
        )

    def append(self, job_id: str, index: int, encoded_data: str) -> None:
        """Decode and append exactly the next expected bounded chunk."""
        session = self._require_session(job_id)
        try:
            if index != session.next_index:
                raise HostError("chunk_out_of_order", "The EML chunks are not in strict order.")
            if index >= session.chunk_count:
                raise HostError("unexpected_chunk", "The transfer contains too many EML chunks.")
            try:
                decoded = base64.b64decode(encoded_data, validate=True)
            except (binascii.Error, ValueError) as error:
                raise HostError("invalid_base64", "An EML chunk is not valid Base64.") from error
            if len(decoded) > MAX_RAW_CHUNK_BYTES:
                raise HostError("chunk_too_large", "An EML chunk exceeds the 512 KiB limit.")
            if session.received_bytes + len(decoded) > session.total_bytes:
                raise HostError(
                    "byte_count_mismatch", "The EML transfer exceeds its declared size."
                )
            session.stream.write(decoded)
            session.digest.update(decoded)
            session.received_bytes += len(decoded)
            session.next_index += 1
        except HostError:
            self.cancel(job_id)
            raise

    def commit(self, job_id: str) -> Path:
        """Close and return the EML file only after count, size, and digest verification."""
        session = self._require_session(job_id)
        self._sessions.pop(job_id)
        session.stream.close()
        if session.next_index != session.chunk_count:
            session.path.unlink(missing_ok=True)
            raise HostError("missing_chunks", "One or more EML chunks are missing.")
        if session.received_bytes != session.total_bytes:
            session.path.unlink(missing_ok=True)
            raise HostError("byte_count_mismatch", "The EML byte count does not match.")
        if session.digest.hexdigest() != session.expected_sha256:
            session.path.unlink(missing_ok=True)
            raise HostError("checksum_mismatch", "The EML SHA-256 checksum does not match.")
        return session.path

    def cancel(self, job_id: str) -> bool:
        """Remove an in-progress transfer and its temporary EML file."""
        session = self._sessions.pop(job_id, None)
        if session is None:
            return False
        session.stream.close()
        session.path.unlink(missing_ok=True)
        return True

    def cleanup_all(self) -> None:
        """Delete every incomplete EML when the native port closes."""
        for job_id in tuple(self._sessions):
            self.cancel(job_id)

    def _require_session(self, job_id: str) -> _TransferSession:
        """Return one active session without silently accepting an unknown job."""
        session = self._sessions.get(job_id)
        if session is None:
            raise HostError("unknown_job", "The transfer job is not active.")
        return session
