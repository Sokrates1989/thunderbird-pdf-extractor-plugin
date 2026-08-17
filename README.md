# Thunderbird PDF Archiver

Thunderbird PDF Archiver is a Thunderbird 128+ MailExtension with a local
Windows companion. It saves one explicitly chosen email and selected supported
attachments as one searchable PDF in an existing local folder. The source
message is never moved, marked, or deleted, and there is no Paperless upload or
credential storage.

## Release 0.5.0 scope

The add-on is now consistently named **Thunderbird PDF Archiver** and includes
a dedicated PDF icon. Its popup, settings, context menu, validation messages,
and errors are available in German and English. Windows Setup asks for the
initial language; the saved language selector in the add-on settings can change
it at any time.

Thunderbird AI Assistant 2.9.0 and newer can hand one explicitly chosen
dashboard message to this add-on through a versioned cross-extension request.
Only the fixed AI Assistant extension ID is accepted. The request opens this
add-on's normal review window; Thunderbird AI Assistant never receives raw mail,
attachments, output paths, native-host access, or PDF results.

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

Release 0.3.0 introduced a redacted local diagnostic snapshot, a bounded rotating
JSONL audit trail, artifact-version and SHA-256 checks during installation, and
a portable Windows release ZIP. The diagnostic data never contains email
content, filenames, URLs, attachment names, or local paths.

## Prerequisites

- Windows 11;
- Thunderbird 128 ESR or newer;
- Node.js 20.18 or newer for extension development;
- Python 3.12 for development only; the packaged host is a standalone `.exe`;
- optional LibreOffice for Office/ODF attachment conversion.

## Install on Windows

Download and run
`Thunderbird-PDF-Archiver-Setup-0.5.0-win-x64.exe`. The per-user setup requires
no administrator privileges. It installs the native companion, registers it for
32- and 64-bit Thunderbird, and installs or updates the XPI in every existing
Thunderbird profile. New profiles can discover the same registered XPI.

If Thunderbird is running, setup asks for confirmation, requests a normal
shutdown, waits for open-draft prompts, and starts Thunderbird again when setup
finishes. It never force-terminates Thunderbird. On a first installation,
Thunderbird may show one final security prompt to enable the side-loaded add-on.
After accepting it, open the add-on settings, choose an existing output folder,
and run **Run diagnostics**.

Run a newer setup directly over the installed version; do not uninstall first.
To remove the product, use Windows **Installed apps**. Exported PDFs are never
removed.

The current test setup is not Authenticode-signed, so Windows SmartScreen may
show an unknown-publisher warning. Verify its published SHA-256 before running
it. A public release should be code-signed.

## Build

From PowerShell at the repository root:

```powershell
winget install --id JRSoftware.InnoSetup --exact
powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\build.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\test-setup.ps1
```

The build creates the primary setup at
`artifacts\Thunderbird-PDF-Archiver-Setup-0.5.0-win-x64.exe`. The isolated setup
test uses private LocalAppData and registry targets and removes them again. It
does not access a real Thunderbird profile.

The legacy PowerShell installer and standalone XPI remain available for
development diagnostics. They are no longer the recommended user workflow.

Setup writes below `%LOCALAPPDATA%\ThunderbirdPdfArchiver\0.5.0` and registers
the native host under the current user at
`HKCU\Software\Mozilla\NativeMessagingHosts\de.sokrates1989.thunderbird_pdf_archiver`.
Administrator privileges are not required.

The build also creates
`artifacts\thunderbird-pdf-archiver-0.5.0-windows.zip`. A clean Windows user can
extract this ZIP, run `installer\windows\install.ps1`, and install the included
XPI without Node.js, Python, or administrator rights.

## Update from an earlier slice

Do not uninstall the old version first. Run the setup EXE. It closes Thunderbird
safely, updates an existing profile XPI in place, installs the registered XPI for
new profiles, and starts Thunderbird again. The fixed add-on ID preserves the
configured output folder, image mode, separator preference, and language.

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

The recommended setup registers an entry under Windows **Installed apps**. Its
uninstaller removes the registered XPI, profile XPI copies, native companion,
manifest, and audit logs. The legacy development installation can still be
removed with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\uninstall.ps1
```

The script asks for confirmation before removing registered companion versions.
Generated PDFs remain untouched.
