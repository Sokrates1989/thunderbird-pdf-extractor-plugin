# Troubleshooting

## “Native host has exited” or host not found

Run `installer\windows\install.ps1`, restart Thunderbird, and verify the current
user registry key points to the generated manifest:

```text
HKCU\Software\Mozilla\NativeMessagingHosts\de.sokrates1989.thunderbird_pdf_archiver
```

The manifest `path` must point to `thunderbird-pdf-archiver-host.exe`, and
`allowed_extensions` must contain
`thunderbird-pdf-archiver@sokrates1989.de`. Extension and host must both be
version `0.2.1`; an older Slice 1 companion is intentionally incompatible.

## Output directory error

Use **Browse / Durchsuchen …** to choose an existing directory. Confirm the
current Windows user can create files there and run **Test companion**. The
companion deliberately does not create a manually typed directory.

## An email-body image is a placeholder

Choose **Embed images, otherwise use placeholders** in the review. Verified
MIME/data and bounded public HTTPS raster images are eligible. HTTP,
private-network, SVG, oversized, unavailable, and invalid sources stay as
placeholders. ReportLab fallback is text-normalized and also uses placeholders.
External embedding can reveal your public IP; placeholder mode avoids requests.

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
