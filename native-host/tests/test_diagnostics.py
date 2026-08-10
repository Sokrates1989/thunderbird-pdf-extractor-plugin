"""Diagnostic tests prove rotation and strict omission of user-derived content."""

from __future__ import annotations

import json
from pathlib import Path

from paperless_mail_archiver.diagnostics import RedactedAuditLog


def test_audit_log_writes_only_allow_listed_fields(tmp_path: Path) -> None:
    """Structured events cannot accept or serialize paths, filenames, or free-form messages."""
    path = tmp_path / "host.jsonl"
    audit = RedactedAuditLog(path)

    audit.record(
        "protocol_error",
        code="invalid_message",
        message_type="archive_commit",
        outcome="error",
        stage="processing",
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload) == {"timestamp", "event", "code", "messageType", "outcome", "stage"}
    assert payload["event"] == "protocol_error"
    assert str(tmp_path) not in path.read_text(encoding="utf-8")


def test_audit_log_redacts_unexpected_tokens_and_rotates(tmp_path: Path) -> None:
    """Unexpected dynamic values are replaced and owned backups stay within their limit."""
    path = tmp_path / "host.jsonl"
    audit = RedactedAuditLog(path, maximum_bytes=100, backup_count=2)

    audit.record("bad event with spaces", code="C:\\private\\mail.eml")
    audit.record("second_event", outcome="success")
    audit.record("third_event", outcome="success")

    combined = "".join(
        candidate.read_text(encoding="utf-8")
        for candidate in (path, path.with_name("host.jsonl.1"), path.with_name("host.jsonl.2"))
        if candidate.exists()
    )
    assert '"event":"redacted"' in combined
    assert "private" not in combined
    assert path.with_name("host.jsonl.1").exists()
