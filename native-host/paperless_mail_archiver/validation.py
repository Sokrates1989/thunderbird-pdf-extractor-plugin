"""Strict runtime validation helpers for untrusted extension messages."""

from collections.abc import Mapping

from paperless_mail_archiver.errors import HostError

PROTOCOL_VERSION = "1.0"
MAX_TITLE_LENGTH = 300
MAX_FILE_NAME_LENGTH = 220


def require_protocol(message: Mapping[str, object]) -> None:
    """Reject messages for a protocol version this component cannot process."""
    if require_string(message, "protocolVersion", maximum=16) != PROTOCOL_VERSION:
        raise HostError("incompatible_protocol", "The Native Messaging protocol is incompatible.")


def require_string(
    message: Mapping[str, object],
    key: str,
    *,
    maximum: int,
    allow_empty: bool = False,
) -> str:
    """Read a bounded string field from a protocol object."""
    value = message.get(key)
    if not isinstance(value, str):
        raise HostError("invalid_message", f"The {key} field must be a string.")
    if (not allow_empty and value == "") or len(value) > maximum:
        raise HostError("invalid_message", f"The {key} field has an invalid length.")
    return value


def require_integer(
    message: Mapping[str, object],
    key: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    """Read a bounded integer field while rejecting booleans."""
    value = message.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise HostError("invalid_message", f"The {key} field must be a bounded integer.")
    return value


def require_boolean(message: Mapping[str, object], key: str) -> bool:
    """Read a strict boolean field."""
    value = message.get(key)
    if not isinstance(value, bool):
        raise HostError("invalid_message", f"The {key} field must be a boolean.")
    return value


def require_mapping(message: Mapping[str, object], key: str) -> Mapping[str, object]:
    """Read a string-keyed nested protocol object."""
    value = message.get(key)
    if not isinstance(value, dict) or not all(isinstance(item, str) for item in value):
        raise HostError("invalid_message", f"The {key} field must be an object.")
    return value


def require_integer_list(
    message: Mapping[str, object],
    key: str,
    *,
    minimum: int,
    maximum: int,
    maximum_items: int,
) -> tuple[int, ...]:
    """Read a bounded JSON integer array while rejecting booleans and duplicates."""
    value = message.get(key)
    if not isinstance(value, list) or len(value) > maximum_items:
        raise HostError("invalid_message", f"The {key} field must be a bounded array.")
    result: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int) or not minimum <= item <= maximum:
            raise HostError("invalid_message", f"The {key} field contains an invalid integer.")
        result.append(item)
    if len(result) != len(set(result)):
        raise HostError("invalid_message", f"The {key} field contains duplicate values.")
    return tuple(result)
