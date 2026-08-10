"""Native Messaging host controller and process entry point."""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from threading import Event, Lock, Thread
from typing import cast

from paperless_mail_archiver import __version__
from paperless_mail_archiver.archive_service import ArchiveService
from paperless_mail_archiver.attachment_support import detect_libreoffice
from paperless_mail_archiver.diagnostics import RedactedAuditLog, create_default_audit_log
from paperless_mail_archiver.errors import CancelledError, HostError
from paperless_mail_archiver.models import ArchiveMetadata, ArchiveRequest, ImageMode
from paperless_mail_archiver.output_store import (
    test_output_directory_writable,
    validate_output_directory,
)
from paperless_mail_archiver.protocol_io import MessageWriter, read_message
from paperless_mail_archiver.renderers import detect_chromium
from paperless_mail_archiver.transfer import MAX_CHUNKS, MAX_RAW_MESSAGE_BYTES, TransferManager
from paperless_mail_archiver.validation import (
    MAX_FILE_NAME_LENGTH,
    MAX_TITLE_LENGTH,
    PROTOCOL_VERSION,
    require_boolean,
    require_integer,
    require_integer_list,
    require_mapping,
    require_protocol,
    require_string,
)
from paperless_mail_archiver.windows_integration import (
    choose_output_directory,
    open_output_directory,
)

JOB_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,64}$")
MAX_BASE64_CHUNK_CHARACTERS = 700_000

FolderPicker = Callable[[Path | None, str], Path | None]
DirectoryOpener = Callable[[Path], None]


class NativeHost:
    """Validate protocol messages and coordinate cancellable archive workers."""

    def __init__(
        self,
        writer: MessageWriter,
        archive_service: ArchiveService | None = None,
        folder_picker: FolderPicker = choose_output_directory,
        directory_opener: DirectoryOpener = open_output_directory,
        audit_log: RedactedAuditLog | None = None,
    ) -> None:
        """Initialize isolated protocol, transfer, configuration, and worker state."""
        self._writer = writer
        libreoffice_executable = detect_libreoffice()
        self._archive_service = archive_service or ArchiveService(
            libreoffice_executable=libreoffice_executable
        )
        self._libreoffice_available = libreoffice_executable is not None
        self._folder_picker = folder_picker
        self._directory_opener = directory_opener
        self._audit_log = audit_log or RedactedAuditLog(None)
        self._transfers = TransferManager()
        self._output_directory: Path | None = None
        self._metadata: dict[str, ArchiveMetadata] = {}
        self._cancellations: dict[str, Event] = {}
        self._workers: dict[str, Thread] = {}
        self._worker_lock = Lock()

    def handle(self, message: Mapping[str, object]) -> None:
        """Dispatch one validated request and emit a small response."""
        message_type = require_string(message, "type", maximum=32)
        require_protocol(message)
        if message_type != "archive_chunk":
            self._audit_log.record("protocol_request", message_type=message_type)
        if message_type == "hello":
            self._handle_hello(message)
        elif message_type == "configure":
            self._handle_configure(message)
        elif message_type == "connection_test":
            self._handle_connection_test()
        elif message_type == "capabilities":
            self._handle_capabilities()
        elif message_type == "diagnostics":
            self._handle_diagnostics()
        elif message_type == "choose_directory":
            self._handle_choose_directory(message)
        elif message_type == "open_output_directory":
            self._handle_open_output_directory()
        elif message_type == "archive_start":
            self._handle_archive_start(message)
        elif message_type == "archive_chunk":
            self._handle_archive_chunk(message)
        elif message_type == "archive_commit":
            self._handle_archive_commit(message)
        elif message_type == "cancel":
            self._handle_cancel(message)
        else:
            raise HostError("unknown_message_type", "The protocol message type is not supported.")

    def shutdown(self) -> None:
        """Cancel active work and remove all incomplete transfer files on port closure."""
        self._transfers.cleanup_all()
        with self._worker_lock:
            cancellations = tuple(self._cancellations.values())
            workers = tuple(self._workers.values())
        for cancellation in cancellations:
            cancellation.set()
        for worker in workers:
            worker.join(timeout=5)
        self._audit_log.record("host_shutdown", outcome="complete")

    def _handle_hello(self, message: Mapping[str, object]) -> None:
        """Return explicit compatible component and protocol versions."""
        extension_version = require_string(message, "componentVersion", maximum=32)
        self._writer.write(
            {
                "compatible": extension_version == __version__,
                "hostVersion": __version__,
                "protocolVersion": PROTOCOL_VERSION,
                "type": "hello",
            }
        )

    def _handle_configure(self, message: Mapping[str, object]) -> None:
        """Validate and retain the current non-secret output folder for this port."""
        raw_directory = require_string(message, "outputDirectory", maximum=32_767)
        self._output_directory = validate_output_directory(Path(raw_directory))
        self._writer.write({"protocolVersion": PROTOCOL_VERSION, "type": "configured"})

    def _handle_connection_test(self) -> None:
        """Verify that the configured directory permits a create-and-delete probe."""
        directory = self._require_output_directory()
        test_output_directory_writable(directory)
        self._writer.write({"protocolVersion": PROTOCOL_VERSION, "type": "connection_ok"})

    def _handle_capabilities(self) -> None:
        """Expose only local converter availability needed for review-time decisions."""
        self._writer.write(
            {
                "libreOfficeAvailable": self._libreoffice_available,
                "protocolVersion": PROTOCOL_VERSION,
                "type": "capabilities",
            }
        )

    def _handle_diagnostics(self) -> None:
        """Return a structured support snapshot without exposing user paths or message data."""
        if self._output_directory is None:
            output_status = "not_configured"
        else:
            try:
                test_output_directory_writable(self._output_directory)
            except HostError:
                output_status = "not_writable"
            else:
                output_status = "writable"
        self._writer.write(
            {
                "auditLogAvailable": self._audit_log.available,
                "chromiumAvailable": detect_chromium() is not None,
                "hostVersion": __version__,
                "libreOfficeAvailable": self._libreoffice_available,
                "outputDirectoryStatus": output_status,
                "packaged": bool(getattr(sys, "frozen", False)),
                "platform": "windows" if os.name == "nt" else "other",
                "protocolVersion": PROTOCOL_VERSION,
                "type": "diagnostics",
            }
        )
        self._audit_log.record("diagnostics_created", outcome=output_status)

    def _handle_choose_directory(self, message: Mapping[str, object]) -> None:
        """Open the native folder picker and return either its selection or cancellation."""
        raw_initial = require_string(
            message,
            "initialDirectory",
            maximum=32_767,
            allow_empty=True,
        )
        title = require_string(message, "title", maximum=160)
        selected = self._folder_picker(Path(raw_initial) if raw_initial else None, title)
        response: dict[str, object] = {
            "protocolVersion": PROTOCOL_VERSION,
            "selected": selected is not None,
            "type": "directory_selected",
        }
        if selected is not None:
            response["outputDirectory"] = str(selected)
        self._writer.write(response)

    def _handle_open_output_directory(self) -> None:
        """Open the configured output directory after validating it again."""
        self._directory_opener(self._require_output_directory())
        self._writer.write({"protocolVersion": PROTOCOL_VERSION, "type": "directory_opened"})

    def _handle_archive_start(self, message: Mapping[str, object]) -> None:
        """Validate job metadata and allocate a bounded EML transfer."""
        self._require_output_directory()
        job_id = self._job_id(message)
        metadata_message = require_mapping(message, "metadata")
        image_mode = require_string(metadata_message, "imageMode", maximum=16)
        if image_mode not in {"placeholder", "embed"}:
            raise HostError("invalid_message", "The imageMode field is unsupported.")
        metadata = ArchiveMetadata(
            title=require_string(metadata_message, "title", maximum=MAX_TITLE_LENGTH),
            file_name=require_string(
                metadata_message,
                "fileName",
                maximum=MAX_FILE_NAME_LENGTH,
            ),
            include_body=require_boolean(metadata_message, "includeBody"),
            attachment_count=require_integer(
                metadata_message,
                "attachmentCount",
                minimum=0,
                maximum=10_000,
            ),
            image_mode=cast(ImageMode, image_mode),
            selected_attachment_indices=require_integer_list(
                metadata_message,
                "selectedAttachmentIndices",
                minimum=0,
                maximum=9_999,
                maximum_items=10_000,
            ),
            separator_pages=require_boolean(metadata_message, "separatorPages"),
        )
        self._transfers.start(
            job_id,
            require_integer(message, "totalBytes", minimum=1, maximum=MAX_RAW_MESSAGE_BYTES),
            require_integer(message, "chunkCount", minimum=1, maximum=MAX_CHUNKS),
            require_string(message, "sha256", maximum=64),
        )
        self._metadata[job_id] = metadata
        self._audit_log.record("archive_transfer_started", outcome="accepted")
        self._writer.write(
            {"jobId": job_id, "protocolVersion": PROTOCOL_VERSION, "type": "archive_started"}
        )

    def _handle_archive_chunk(self, message: Mapping[str, object]) -> None:
        """Append one strict-order Base64 chunk and acknowledge only after writing it."""
        job_id = self._job_id(message)
        index = require_integer(message, "index", minimum=0, maximum=MAX_CHUNKS - 1)
        encoded = require_string(message, "data", maximum=MAX_BASE64_CHUNK_CHARACTERS)
        try:
            self._transfers.append(job_id, index, encoded)
        except HostError:
            self._metadata.pop(job_id, None)
            raise
        self._writer.write(
            {
                "index": index,
                "jobId": job_id,
                "protocolVersion": PROTOCOL_VERSION,
                "type": "chunk_received",
            }
        )

    def _handle_archive_commit(self, message: Mapping[str, object]) -> None:
        """Verify the transfer and start rendering while continuing to accept cancellation."""
        job_id = self._job_id(message)
        metadata = self._metadata.pop(job_id, None)
        if metadata is None:
            raise HostError("unknown_job", "The archive job metadata is not active.")
        eml_path = self._transfers.commit(job_id)
        cancellation = Event()
        request = ArchiveRequest(
            eml_path=eml_path,
            metadata=metadata,
            output_directory=self._require_output_directory(),
            cancellation=cancellation,
        )
        worker = Thread(
            target=self._run_archive,
            args=(job_id, request),
            daemon=True,
            name=f"archive-{job_id}",
        )
        with self._worker_lock:
            self._cancellations[job_id] = cancellation
            self._workers[job_id] = worker
        worker.start()

    def _handle_cancel(self, message: Mapping[str, object]) -> None:
        """Cancel either an incomplete transfer or a running renderer."""
        job_id = self._job_id(message)
        if self._transfers.cancel(job_id):
            self._metadata.pop(job_id, None)
            self._audit_log.record("archive_cancelled", stage="transfer")
            self.write_error(CancelledError(), job_id=job_id)
            return
        with self._worker_lock:
            cancellation = self._cancellations.get(job_id)
        if cancellation is None:
            raise HostError("unknown_job", "The archive job is not active.")
        cancellation.set()
        self._audit_log.record("archive_cancel_requested", stage="processing")

    def _run_archive(self, job_id: str, request: ArchiveRequest) -> None:
        """Run one archive worker and reduce all failures to redacted protocol errors."""
        try:
            result = self._archive_service.archive(
                request,
                lambda stage, completed, total, detail: self._writer.write(
                    {
                        "completed": completed,
                        "detail": detail,
                        "jobId": job_id,
                        "protocolVersion": PROTOCOL_VERSION,
                        "stage": stage,
                        "total": total,
                        "type": "progress",
                    }
                ),
            )
            self._writer.write(
                {
                    "jobId": job_id,
                    "outputPath": str(result.output_path),
                    "pageCount": result.page_count,
                    "includedAttachments": list(result.included_attachments),
                    "skippedAttachments": list(result.skipped_attachments),
                    "protocolVersion": PROTOCOL_VERSION,
                    "type": "success",
                }
            )
            self._audit_log.record("archive_completed", outcome="success")
        except HostError as error:
            self.write_error(error, job_id=job_id)
        except Exception:
            self.write_error(
                HostError("internal_error", "The native host encountered an unexpected error."),
                job_id=job_id,
            )
        finally:
            request.eml_path.unlink(missing_ok=True)
            with self._worker_lock:
                self._cancellations.pop(job_id, None)
                self._workers.pop(job_id, None)

    def _require_output_directory(self) -> Path:
        """Return the configured output folder or a stable setup error."""
        if self._output_directory is None:
            raise HostError("not_configured", "Configure an output directory before archiving.")
        return self._output_directory

    @staticmethod
    def _job_id(message: Mapping[str, object]) -> str:
        """Read a bounded identifier that is safe for logs and thread names."""
        job_id = require_string(message, "jobId", maximum=64)
        if JOB_ID_PATTERN.fullmatch(job_id) is None:
            raise HostError("invalid_job_id", "The job ID contains invalid characters.")
        return job_id

    def write_error(self, error: HostError, *, job_id: str | None = None) -> None:
        """Emit a bounded error without exception details or email content."""
        response: dict[str, object] = {
            "code": error.code,
            "message": str(error),
            "protocolVersion": PROTOCOL_VERSION,
            "type": "error",
        }
        if job_id is not None:
            response["jobId"] = job_id
        self._writer.write(response)
        self._audit_log.record("protocol_error", code=error.code, outcome="error")


def main() -> None:
    """Run the framed stdin/stdout host loop until Thunderbird closes the port."""
    if sys.argv[1:] == ["--version"]:
        sys.stdout.write(f"{__version__}\n")
        return
    writer = MessageWriter(sys.stdout.buffer)
    host = NativeHost(writer, audit_log=create_default_audit_log())
    try:
        while True:
            try:
                message = read_message(sys.stdin.buffer)
            except HostError as error:
                host.write_error(error)
                break
            if message is None:
                break
            try:
                host.handle(message)
            except HostError as error:
                host.write_error(error)
    finally:
        host.shutdown()


if __name__ == "__main__":
    main()
