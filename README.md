# Thunderbird PDF Archiver

Thunderbird PDF Archiver is a Thunderbird 128+ MailExtension with a local
Windows companion. It saves one explicitly chosen email and selected supported
attachments as one searchable PDF in an existing local folder. The source
message is never moved, marked, or deleted, and there is no Paperless upload or
credential storage.

## Release 0.3.0 scope

The review popup shows every Thunderbird-detected item with filename, MIME type,
size, support status, and selection state. Supported real attachments are
selected by default; inline body images and unsupported files are disabled and
unchecked. The first PDF section discloses which files are included or skipped,
and the final result repeats the included/skipped filenames.

The companion merges sections in original MIME order:

1. searchable email content;
2. PDF attachments without rasterization, including files readable with an
   empty user password after safe decryption;
3. PNG, JPEG, WebP, BMP, and single- or multi-frame TIFF images;
4. searchable TXT and CSV output;
5. sanitized HTML through the same local renderer;
6. nested EML files, recursively to a bounded depth; and
7. DOCX, XLSX, PPTX, ODT, ODS, and ODP when local LibreOffice is available.

ZIP/archive and unknown formats are not expanded. They remain visible as
skipped. Optional separator pages are off by default. PDF outlines are always
created for the email and every included attachment, including nested EML
children.

Email-body images retain the privacy-first option introduced in Slice 1:
placeholders are the default, or the user may explicitly request bounded
embedding with per-image placeholder fallback. A placeholder backed by a safe
web source or enclosing web link remains clickable. Readable link labels are
preserved without printing long tracking destinations beside them.

Release 0.3.0 adds a redacted local diagnostic snapshot, a bounded rotating
JSONL audit trail, artifact-version and SHA-256 checks during installation, and
a portable Windows release ZIP. The diagnostic data never contains email
content, filenames, URLs, attachment names, or local paths.

## Prerequisites

- Windows 11;
- Thunderbird 128 ESR or newer;
- Node.js 20.18 or newer for extension development;
- Python 3.12 for development only; the packaged host is a standalone `.exe`;
- optional LibreOffice for Office/ODF attachment conversion.

## Build and install

From PowerShell at the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\build.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\install.ps1
```

Then install `artifacts\thunderbird-pdf-archiver-0.3.0.xpi` in Thunderbird via
Add-ons and Themes → Extensions → Install Add-on From File. Restart Thunderbird,
open the extension settings, select an existing folder with **Browse**, and run
**Run diagnostics** before the first archive.

The installer writes below `%LOCALAPPDATA%\ThunderbirdPdfArchiver\0.3.0` and
registers the native host under the current user at
`HKCU\Software\Mozilla\NativeMessagingHosts\de.sokrates1989.thunderbird_pdf_archiver`.
Administrator privileges are not required.

The build also creates
`artifacts\thunderbird-pdf-archiver-0.3.0-windows.zip`. A clean Windows user can
extract this ZIP, run `installer\windows\install.ps1`, and install the included
XPI without Node.js, Python, or administrator rights.

## Update from an earlier slice

Do not uninstall the old version first. Close Thunderbird, extract the new
release, run
`powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\install.ps1`,
then install the new XPI over the existing add-on and restart Thunderbird. The
fixed add-on ID lets Thunderbird
treat this as an update, so the configured output folder, image mode, and
separator preference remain in extension storage. The native-host registry
entry is repointed to 0.3.0 after the copied executable passes its version and
SHA-256 checks.

## PDF links in browser viewers

The exported PDF retains only safe `http`, `https`, and `mailto` URI actions.
The PDF format has no standard new-tab flag for these URI actions, so the viewer
controls normal-click behavior. Use **Ctrl+click** or the middle mouse button to
open a link in a new browser tab. The extension deliberately does not add PDF
JavaScript or `Launch` actions to force navigation.

## Development validation

```powershell
Set-Location extension
npm ci
npm run typecheck
npm run lint
npm test
npm run package

Set-Location ..\native-host
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy paperless_mail_archiver tests
.\.venv\Scripts\python.exe -m pytest
```

See [architecture](docs/architecture.md), [security](docs/security.md),
[protocol](docs/protocol.md), [testing](docs/testing.md), the
[Slice 3 acceptance contract](docs/slice-3-acceptance.md), and
[troubleshooting](docs/troubleshooting.md).

## Uninstall

Remove the Thunderbird extension in Add-ons and Themes, then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\uninstall.ps1
```

The script asks for confirmation before removing registered companion versions.
Generated PDFs remain untouched.
