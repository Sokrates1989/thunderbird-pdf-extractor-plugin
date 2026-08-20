# Troubleshooting

## “Native host has exited” or host not found

On Windows, run `installer\windows\install.ps1`, restart Thunderbird, and verify
the current-user registry key points to the generated manifest:

```text
HKCU\Software\Mozilla\NativeMessagingHosts\de.sokrates1989.thunderbird_pdf_archiver
```

The manifest `path` must point to `thunderbird-pdf-archiver-host.exe`, and
`allowed_extensions` must contain
`thunderbird-pdf-archiver@sokrates1989.de`. Extension and host must both be
version `0.6.0`; an older companion is intentionally incompatible.

For the recommended installation, rerun
`Thunderbird-PDF-Archiver-Setup-0.6.0-win-x64.exe`. It repairs the profile XPI,
both 32-/64-bit native-host registrations, and the installed manifest together.

On macOS, rerun the package matching the Mac architecture and verify this file
exists for the current user:

```text
~/Library/Application Support/Mozilla/NativeMessagingHosts/de.sokrates1989.thunderbird_pdf_archiver.json
```

Its `path` must be absolute and point to the executable below
`~/Library/Application Support/Thunderbird PDF Archiver`. Restart Thunderbird
after repairing the installation.

## Setup cannot close Thunderbird

Setup never force-terminates Thunderbird. Save or discard every open compose
draft, close remaining Thunderbird windows, and rerun setup. If background
processes remain, end Thunderbird normally from its menu before trying again.

## Windows warns about an unknown publisher

The current test installer is not Authenticode-signed. Compare the downloaded
file's SHA-256 with the checksum published on the GitHub release. Do not bypass
the warning if the checksum differs. Public releases should be code-signed.

## Output directory error

Use **Browse / Durchsuchen …** to choose an existing directory. Confirm the
current Windows user can create files there, then run **Run diagnostics /
Diagnose ausführen**. The companion deliberately does not create a manually
typed directory.

## Collect redacted diagnostics

Open the extension settings and select **Run diagnostics / Diagnose ausführen**.
The displayed snapshot contains versions and readiness states only. The rotating
native log is stored at
`%LOCALAPPDATA%\ThunderbirdPdfArchiver\logs\host.jsonl`; it contains no mail
content, filenames, URLs, attachment names, or local paths.

On macOS, the same bounded log is stored at
`~/Library/Application Support/ThunderbirdPdfArchiver/logs/host.jsonl`.

## A PDF link replaces the current tab

Use **Ctrl+click** or the middle mouse button in the browser PDF viewer. Safe PDF
web links are URI actions, and that action type has no standard new-window flag.
The viewer therefore owns ordinary-click behavior. The archive does not use
JavaScript, `Launch`, or other active PDF actions to override it.

## An email-body image is a placeholder

Choose **Embed images, otherwise use placeholders** in the review. Verified
MIME/data and bounded public HTTPS raster images are eligible. HTTP,
private-network, SVG, oversized, unavailable, and invalid sources stay as
placeholders. ReportLab fallback is text-normalized and also uses placeholders.
External embedding can reveal your public IP; placeholder mode avoids requests.
When a public HTTPS image cannot be embedded, its placeholder links to the
image source unless the image was already wrapped by a safe link, in which case
that existing destination is retained. The PDF viewer controls whether it shows
or requires confirmation for an external destination; the PDF itself cannot
enforce one consistent confirmation dialog across viewers.

The original email must actually contain image data or reachable image URLs.
Many newsletters contain only remote URLs, so there is nothing to extract from
the EML itself. The companion requests only formats it can verify (PNG, GIF,
JPEG, and WebP), applies strict size/time/network limits, and falls back per
image when a host is unavailable or rejects the request.

## Browser rendering falls back

Edge, Chrome, or Chromium may be missing, blocked, or unable to print within 60
seconds. The host then uses ReportLab. The normalized fallback remains readable
and searchable but is not visually identical to the email.

## An attachment is unchecked or missing

- Inline images are part of the email body and are never appended separately.
- ZIP/archive and unknown formats are unsupported and remain unchecked.
- DOCX/XLSX/PPTX/ODT/ODS/ODP require an installed local LibreOffice. Restart
  Thunderbird after installing it so a new companion process reports the
  capability.
- A supported attachment can be intentionally unchecked before saving; it will
  appear in the PDF and success view as skipped.
- A PDF readable with an empty user password is safely normalized before merge.
  A selected corrupt or genuinely password-required PDF still aborts the entire
  job and names the failed attachment instead of silently omitting it.

## Existing file was not replaced

No overwrite is permitted. Repeated saves use `name (2).pdf`, `name (3).pdf`,
and so on.

## Development build fails

Use Node.js 20.18+ and Python 3.12. Recreate `native-host\.venv` if it uses a
different Python minor version. Use `npm ci` and the checked-in hash-locked
`requirements.lock`; regenerate locks only when intentionally changing pinned
dependencies.
