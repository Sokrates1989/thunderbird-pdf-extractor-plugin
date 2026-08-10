"""Host-controller tests cover explicit component compatibility handshakes."""

import io
from pathlib import Path

import pytest

from paperless_mail_archiver.errors import HostError
from paperless_mail_archiver.host import NativeHost
from paperless_mail_archiver.protocol_io import MessageWriter, read_message


def _hello(component_version: str) -> dict[str, object]:
    """Send one hello message and decode its framed response."""
    stream = io.BytesIO()
    host = NativeHost(MessageWriter(stream))
    host.handle(
        {
            "componentVersion": component_version,
            "protocolVersion": "1.0",
            "type": "hello",
        }
    )
    stream.seek(0)
    response = read_message(stream)
    assert response is not None
    return response


def test_matching_component_handshake_is_compatible() -> None:
    """The released extension and host versions explicitly agree."""
    response = _hello("0.2.2")

    assert response["compatible"] is True
    assert response["hostVersion"] == "0.2.2"


def test_different_component_handshake_is_incompatible() -> None:
    """A different component version is rejected before configuration or EML transfer."""
    response = _hello("0.1.1")

    assert response["compatible"] is False


def test_capabilities_reports_optional_office_converter_as_boolean() -> None:
    """The extension can make a review-time Office selection decision before transfer."""
    stream = io.BytesIO()
    host = NativeHost(MessageWriter(stream))

    host.handle({"protocolVersion": "1.0", "type": "capabilities"})
    stream.seek(0)
    response = read_message(stream)

    assert response is not None
    assert response["type"] == "capabilities"
    assert isinstance(response["libreOfficeAvailable"], bool)


def test_choose_directory_returns_native_selection(tmp_path: Path) -> None:
    """The host exposes a native picker result without requiring manual path entry."""
    stream = io.BytesIO()
    observed: list[tuple[Path | None, str]] = []

    def picker(initial: Path | None, title: str) -> Path | None:
        observed.append((initial, title))
        return tmp_path

    host = NativeHost(MessageWriter(stream), folder_picker=picker)
    host.handle(
        {
            "initialDirectory": "C:\\Previous",
            "protocolVersion": "1.0",
            "title": "Choose a folder",
            "type": "choose_directory",
        }
    )
    stream.seek(0)
    response = read_message(stream)

    assert observed == [(Path("C:\\Previous"), "Choose a folder")]
    assert response is not None
    assert response["selected"] is True
    assert response["outputDirectory"] == str(tmp_path)


def test_open_directory_uses_only_configured_output(tmp_path: Path) -> None:
    """The open action receives the already validated configured directory."""
    stream = io.BytesIO()
    opened: list[Path] = []
    host = NativeHost(MessageWriter(stream), directory_opener=opened.append)
    host.handle(
        {
            "outputDirectory": str(tmp_path),
            "protocolVersion": "1.0",
            "type": "configure",
        }
    )
    host.handle({"protocolVersion": "1.0", "type": "open_output_directory"})
    stream.seek(0)
    configured = read_message(stream)
    response = read_message(stream)

    assert configured is not None and configured["type"] == "configured"
    assert response is not None and response["type"] == "directory_opened"
    assert opened == [tmp_path.resolve()]


def test_archive_start_rejects_unknown_image_mode(tmp_path: Path) -> None:
    """Only the two reviewed image policies can reach MIME parsing or rendering."""
    stream = io.BytesIO()
    host = NativeHost(MessageWriter(stream))
    host.handle(
        {
            "outputDirectory": str(tmp_path),
            "protocolVersion": "1.0",
            "type": "configure",
        }
    )

    with pytest.raises(HostError, match="imageMode"):
        host.handle(
            {
                "chunkCount": 1,
                "jobId": "invalid-image-mode",
                "metadata": {
                    "attachmentCount": 0,
                    "fileName": "email.pdf",
                    "imageMode": "download-everything",
                    "includeBody": True,
                    "title": "Email",
                },
                "protocolVersion": "1.0",
                "sha256": "0" * 64,
                "totalBytes": 1,
                "type": "archive_start",
            }
        )
