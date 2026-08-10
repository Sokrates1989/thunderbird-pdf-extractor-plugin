"""Mozilla Native Messaging framing for length-prefixed UTF-8 JSON objects."""

from __future__ import annotations

import json
import struct
from collections.abc import Mapping
from threading import Lock
from typing import Any, BinaryIO

from paperless_mail_archiver.errors import HostError

MAX_MESSAGE_BYTES = 1024 * 1024


def read_message(stream: BinaryIO) -> dict[str, object] | None:
    """Read one little-endian framed object, returning ``None`` at clean EOF."""
    header = stream.read(4)
    if header == b"":
        return None
    if len(header) != 4:
        raise HostError("invalid_frame", "The Native Messaging frame header is incomplete.")
    (length,) = struct.unpack("<I", header)
    if length == 0 or length > MAX_MESSAGE_BYTES:
        raise HostError("invalid_frame_size", "The Native Messaging frame size is invalid.")
    payload = stream.read(length)
    if len(payload) != length:
        raise HostError("invalid_frame", "The Native Messaging frame body is incomplete.")
    try:
        value: Any = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HostError(
            "invalid_json", "The Native Messaging payload is not valid JSON."
        ) from error
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise HostError("invalid_message", "The Native Messaging payload must be an object.")
    return dict(value)


class MessageWriter:
    """Serialize protocol writes from the main loop and worker threads."""

    def __init__(self, stream: BinaryIO) -> None:
        """Store the binary output stream and create its write lock."""
        self._stream = stream
        self._lock = Lock()

    def write(self, message: Mapping[str, object]) -> None:
        """Write and flush one response that remains below the protocol ceiling."""
        encoded = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(encoded) > MAX_MESSAGE_BYTES:
            raise HostError("response_too_large", "The native-host response is too large.")
        with self._lock:
            self._stream.write(struct.pack("<I", len(encoded)))
            self._stream.write(encoded)
            self._stream.flush()
