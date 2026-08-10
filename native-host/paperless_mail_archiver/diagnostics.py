"""Bounded, path-free diagnostic logging for local release support."""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

MAX_AUDIT_LOG_BYTES = 512 * 1024
AUDIT_LOG_BACKUPS = 2
_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


class RedactedAuditLog:
    """Write a small rotating JSONL audit trail containing only allow-listed tokens."""

    def __init__(
        self,
        path: Path | None,
        *,
        maximum_bytes: int = MAX_AUDIT_LOG_BYTES,
        backup_count: int = AUDIT_LOG_BACKUPS,
    ) -> None:
        """Configure an optional owned log path and deterministic rotation limits."""
        self._path = path
        self._maximum_bytes = maximum_bytes
        self._backup_count = backup_count
        self._lock = Lock()
        self._available = path is not None

    @property
    def available(self) -> bool:
        """Return whether the audit sink is currently writable in principle."""
        return self._available

    def record(
        self,
        event: str,
        *,
        code: str | None = None,
        message_type: str | None = None,
        outcome: str | None = None,
        stage: str | None = None,
    ) -> None:
        """Append one event without accepting paths, filenames, messages, or mail data."""
        path = self._path
        if path is None or not self._available:
            return
        payload = {
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "event": self._safe_token(event),
        }
        for key, value in (
            ("code", code),
            ("messageType", message_type),
            ("outcome", outcome),
            ("stage", stage),
        ):
            if value is not None:
                payload[key] = self._safe_token(value)
        encoded = (json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n").encode(
            "utf-8"
        )
        try:
            with self._lock:
                path.parent.mkdir(parents=True, exist_ok=True)
                self._rotate_if_needed(path, len(encoded))
                with path.open("ab") as stream:
                    stream.write(encoded)
                    stream.flush()
                    os.fsync(stream.fileno())
        except OSError:
            self._available = False

    @staticmethod
    def _safe_token(value: str) -> str:
        """Replace any unexpected diagnostic value instead of logging arbitrary text."""
        return value if _SAFE_TOKEN.fullmatch(value) is not None else "redacted"

    def _rotate_if_needed(self, path: Path, incoming_bytes: int) -> None:
        """Rotate only this component's owned audit files before the size ceiling is crossed."""
        if not path.exists() or path.stat().st_size + incoming_bytes <= self._maximum_bytes:
            return
        for index in range(self._backup_count, 0, -1):
            source = path if index == 1 else path.with_name(f"{path.name}.{index - 1}")
            destination = path.with_name(f"{path.name}.{index}")
            if not source.exists():
                continue
            destination.unlink(missing_ok=True)
            source.replace(destination)


def create_default_audit_log() -> RedactedAuditLog:
    """Create the per-user audit sink, or a disabled sink when LocalAppData is unavailable."""
    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if not local_app_data:
        return RedactedAuditLog(None)
    path = Path(local_app_data) / "ThunderbirdPdfArchiver" / "logs" / "host.jsonl"
    return RedactedAuditLog(path)
