# Security and privacy

Protected data includes raw mail, decoded bodies, attachment names and bytes,
generated PDFs, and local paths. The Thunderbird extension is trusted to select
one message and show the review. Every Native Messaging object and all email
content are still validated as untrusted by the companion.

## Controls

- **Remote HTML and tracking:** placeholder mode is the persisted default and
  makes no image request. Explicit embed mode accepts only bounded verified MIME,
  data, or public HTTPS raster images; each failure becomes a placeholder. It can
  reveal the user's IP address to an image host. Sanitized HTML removes scripts,
  remote sources, CSS, fonts, forms, frames, objects, embeds, SVG/MathML, and
  event handlers. Chromium receives a restrictive CSP and only local/data input.
- **Attachment allowlist:** PDF, reviewed raster formats, TXT/CSV, sanitized
  HTML, bounded nested EML, and capability-gated Office/ODF formats are handled.
  Archives and unknown types are never expanded or passed to a shell. Unsupported
  files are disabled in review and disclosed in both output views.
- **PDF active content:** source PDF pages are copied without rasterization, but
  page additional-actions and every annotation except normalized `http`,
  `https`, or `mailto` URI links are removed from the final writer. Retained
  links are rebuilt with only their rectangle, destination, tooltip text, and a
  border-free appearance; JavaScript, launch, chained, and automatic actions do
  not survive. Catalog JavaScript, embedded files, and source document open
  actions are not imported. PDFs accessible with an empty user password are
  rewritten without encryption before merging; password-required files remain
  rejected. Final outlines and metadata are created by the companion.
- **Image bombs:** Pillow warnings become errors. Frame count, per-frame pixels,
  total pixels, decoded attachment bytes, and final page counts are bounded.
  EXIF orientation is applied before aspect-ratio-preserving rendering.
- **Nested messages:** MIME traversal treats attached `message/rfc822` data as
  one top-level attachment. Recursive conversion has a depth limit; descendants
  beyond it are explicitly marked skipped in their parent email section.
- **Office conversion:** support is disabled unless a local LibreOffice
  executable is detected. Conversion uses `shell=False`, a fixed argument array,
  timeout/cancellation, separate input/output directories, and a dedicated
  disposable user profile configured for the **Very High** macro security
  level with no trusted locations. LibreOffice documents that this level
  disables macros outside trusted locations and that headless conversion needs
  a writable profile. See [macro security](https://help.libreoffice.org/latest/en-US/text/shared/optionen/macrosecurity_sl.html)
  and [startup parameters](https://help.libreoffice.org/latest/en-GB/text/shared/guide/start_parameters.html).
- **Oversized or malformed input:** raw EML and decoded attachments are limited
  to 50 MiB, decoded body text to 5 million characters, top-level attachments
  to 500, individual protocol chunks to 512 KiB, transfer jobs to 100 chunks,
  each PDF section to 5,000 pages, and the merged output to 10,000 pages. Strict
  Base64, order, byte-count, and SHA-256 verification precedes MIME parsing.
- **Command injection:** browser and LibreOffice launches use locally detected
  executable paths, argument arrays, `shell=False`, timeouts, and cooperative
  termination. Windows folder selection uses a fixed PowerShell script with user
  strings passed through environment variables. Folder opening receives only
  the validated configured directory.
- **Path and overwrite safety:** the host requires an existing absolute output
  directory, sanitizes Windows filenames, stages a complete PDF in that folder,
  and publishes with no-replace semantics. Collisions receive numbered names.
- **Data residue:** EML, decoded attachment files, sanitized HTML, Chromium and
  LibreOffice profiles, conversion output, partial PDFs, and staging files live
  only in owned temporary directories and are removed on success, failure,
  cancellation, or port closure.
- **Logging:** stdout contains framed protocol messages only. The packaged host
  keeps `host.jsonl` below `%LOCALAPPDATA%\ThunderbirdPdfArchiver\logs`, capped at
  512 KiB with two backups. Its schema accepts only timestamps, fixed event
  tokens, error codes, message types, outcomes, and stages. It cannot accept
  bodies, MIME bytes, filenames, URLs, attachment names, local paths, command
  output, tokens, or arbitrary exception messages. Logging failure never blocks
  archiving.

There is no Paperless token or other credential. Thunderbird `storage.local`
contains only the output directory, image mode, and separator-page preference.
