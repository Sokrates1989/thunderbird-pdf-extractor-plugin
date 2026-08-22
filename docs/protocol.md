# Native Messaging protocol 1.0

Extension and host component version `1.1.0` must match exactly. Messages are
compact UTF-8 JSON objects framed with Mozilla's four-byte little-endian length
prefix. Frames are limited to 1 MiB and every message includes
`protocolVersion: "1.0"`.

## AI Mail Assistant for Thunderbird hand-off

The independent cross-extension protocol is version `1`. The PDF Archiver
background accepts `thunderbird-pdf-archiver:ping` and
`thunderbird-pdf-archiver:open-review` only when Thunderbird reports the sender
ID as `thunderbird-ai@felicitas-wisdom.com`. An open-review request contains one positive,
safe-integer Thunderbird message ID and opens the existing review popup. The
boundary never returns message content, attachments, paths, native-host data, or
PDF results. Unknown senders receive no integration response.

## Session sequence

1. `hello` exchanges component/protocol versions and `compatible`.
2. `capabilities` returns `libreOfficeAvailable`; it exposes no local paths.
   Optional `diagnostics` returns component/readiness booleans and a redacted
   output-folder status, never the configured path, filenames, URLs, or mail data.
3. Optional `choose_directory` passes a bounded title and optional initial path.
   `directory_selected` returns either `selected: false` or the absolute path.
4. `configure` validates an existing absolute `outputDirectory`.
5. Optional `connection_test` creates and removes an empty probe.
6. `archive_start` contains `jobId`, `totalBytes`, `chunkCount`, lowercase
   `sha256`, and metadata:
   - `title`, `fileName`, and `includeBody`;
   - `imageMode`: `placeholder` or `embed`;
   - `attachmentCount`: all reviewed real top-level attachments;
   - `selectedAttachmentIndices`: unique real-attachment ordinals; and
   - `separatorPages`: a strict boolean.
7. Each `archive_chunk` contains the next zero-based index and Base64 data for
   at most 512 KiB decoded bytes. The host acknowledges only after writing.
8. `archive_commit` verifies chunk count, bytes, and SHA-256 before parsing. It
   emits `progress` stages `parsing`, `rendering`, `converting`, `merging`, and
   `saving`. Conversion progress may include a bounded attachment filename.
9. `success` returns `outputPath`, `pageCount`, `includedAttachments`, and
   `skippedAttachments`.
10. Optional `open_output_directory` opens only the configured validated folder.
11. `cancel` deletes an incomplete transfer or signals the active renderer,
    converter, or assembler.

The host rejects duplicate/out-of-range selection indices and any mismatch
between `attachmentCount` and the authoritative MIME parse. Errors use
`{type: "error", code, message}` with optional `jobId`. Attachment failures may
name the bounded filename but never include attachment content, command output,
or raw exception text.

The host never sends EML or PDF bytes back to the extension. Standard output is
reserved exclusively for framed protocol responses.
