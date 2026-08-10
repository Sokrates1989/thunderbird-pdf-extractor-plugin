"""Native Messaging frame tests cover compact Unicode JSON and malformed input."""

import io
import json
import struct

import pytest

from paperless_mail_archiver.errors import HostError
from paperless_mail_archiver.protocol_io import MessageWriter, read_message


def test_round_trip_native_message() -> None:
    """Writer and reader agree on little-endian byte length and UTF-8 content."""
    stream = io.BytesIO()
    MessageWriter(stream).write({"message": "Grüße", "type": "test"})
    stream.seek(0)

    assert read_message(stream) == {"message": "Grüße", "type": "test"}


def test_reader_rejects_non_object_json() -> None:
    """Arrays cannot bypass the protocol object's field validation."""
    payload = json.dumps(["not", "an", "object"]).encode()
    stream = io.BytesIO(struct.pack("<I", len(payload)) + payload)

    with pytest.raises(HostError, match="must be an object"):
        read_message(stream)
