# Thunderbird PDF Archiver

Thunderbird PDF Archiver is a Thunderbird 128+ MailExtension with a local
Windows or macOS companion. It saves one explicitly chosen email and selected
supported attachments as one searchable PDF in an existing local folder. The
source message is never moved, marked, or deleted, and there is no Paperless
upload or credential storage.

## Downloads and releases

- [Latest release](https://github.com/Sokrates1989/thunderbird-pdf-extractor-plugin/releases/latest)
- [Installer and version history](https://github.com/Sokrates1989/thunderbird-pdf-extractor-plugin/releases)
- [Latest Apple silicon installer](https://github.com/Sokrates1989/thunderbird-pdf-extractor-plugin/releases/latest/download/Thunderbird-PDF-Archiver-Setup-macos-arm64.pkg)
- [Latest Intel Mac installer](https://github.com/Sokrates1989/thunderbird-pdf-extractor-plugin/releases/latest/download/Thunderbird-PDF-Archiver-Setup-macos-x86_64.pkg)
- [Latest Windows installer](https://github.com/Sokrates1989/thunderbird-pdf-extractor-plugin/releases/latest/download/Thunderbird-PDF-Archiver-Setup-win-x64.exe)

Stable asset names always select the latest GitHub release. Each release additionally retains versioned installers, the XPI, source, and SHA-256 checksums as its history.

## Release 1.0.1 scope

Release 1.0.1 repairs the per-user macOS Native Messaging registration path so
Thunderbird can launch the packaged companion. Reinstalling also removes the
obsolete manifest from the incorrect Application Support location and provides
an actionable error when registration is missing.

Release 1.0.0 established the permanent publication identity
`thunderbird-pdf@felicitas-wisdom.com`, adopted GPL-3.0-or-later, and added
license acknowledgement to the native installers. It retains the per-user
macOS and Windows packages, localized XPI, architecture-matched companion, and
Mozilla Native Messaging registration without administrator privileges.

Release 0.5.0 consistently named the add-on **Thunderbird PDF Archiver** and added
a dedicated PDF icon. Its popup, settings, context menu, validation messages,
and errors are available in German and English. Windows Setup asks for the
initial language; the saved language selector in the add-on settings can change
it at any time.

Thunderbird AI Assistant 3.0.0 and newer can hand one explicitly chosen
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

- Windows 11 or macOS with the matching Apple silicon/Intel installer;
- Thunderbird 128 ESR or newer;
- Node.js 20.18 or newer for extension development;
- Python 3.12 for development only; the packaged host is a standalone executable;
- optional LibreOffice for Office/ODF attachment conversion.

## Install on macOS

Download and open
`Thunderbird-PDF-Archiver-Setup-1.0.1-macos-arm64.pkg` on Apple silicon, or the
`macos-x86_64` package on an Intel Mac. The Installer runs for the current user
without administrator privileges. It installs or updates the fixed-ID XPI in
every existing Thunderbird profile, installs the standalone native companion,
and registers its absolute path in Mozilla's per-user Native Messaging folder.

Start Thunderbird at least once before running setup so a profile exists.
Review and accept the GNU General Public License, close Thunderbird when
Installer asks, finish setup, then restart Thunderbird. Accept
any one-time add-on activation or permission prompt, open the add-on settings,
choose an existing output folder, and run **Run diagnostics**.

Run a newer package directly over the installed version; do not remove the old
version first. The current package is not Developer ID-signed or notarized. A
downloaded public build can therefore require explicit approval in macOS
**Privacy & Security** after its checksum has been verified.

## Install on Windows

Download and run
`Thunderbird-PDF-Archiver-Setup-1.0.1-win-x64.exe`. The per-user setup requires
no administrator privileges. It installs the native companion, registers it for
32- and 64-bit Thunderbird, and installs or updates the XPI in every existing
Thunderbird profile. New profiles can discover the same registered XPI.

Review and accept the GNU General Public License. If Thunderbird is running,
setup asks for confirmation, requests a normal
shutdown, waits for open-draft prompts, and starts Thunderbird again when setup
finishes. It never force-terminates Thunderbird. On a first installation,
Thunderbird may show one final security prompt to enable the side-loaded add-on.
After accepting it, open the add-on settings, choose an existing output folder,
and run **Run diagnostics**.

Run a newer setup directly over the installed version; do not uninstall first.
To remove the product, use Windows **Installed apps**. Exported PDFs are never
removed.

The native 1.0.1 installers remove the private prerelease identity
`thunderbird-pdf-archiver@sokrates1989.de` before installing the permanent
publication identity. A manual XPI installation requires uninstalling the
prerelease identity once.

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
`artifacts\Thunderbird-PDF-Archiver-Setup-1.0.1-win-x64.exe`. The isolated setup
test uses private LocalAppData and registry targets and removes them again. It
does not access a real Thunderbird profile.

The legacy PowerShell installer and standalone XPI remain available for
development diagnostics. They are no longer the recommended user workflow.

Setup writes below `%LOCALAPPDATA%\ThunderbirdPdfArchiver\1.0.1` and registers
the native host under the current user at
`HKCU\Software\Mozilla\NativeMessagingHosts\de.sokrates1989.thunderbird_pdf_archiver`.
Administrator privileges are not required.

The build also creates
`artifacts\thunderbird-pdf-archiver-1.0.1-windows.zip`. A clean Windows user can
extract this ZIP, run `installer\windows\install.ps1`, and install the included
XPI without Node.js, Python, or administrator rights.

### Build on macOS

Use Node.js 20.18+ and Python 3.12 on the target architecture:

```bash
./installer/macos/build-setup.sh --python /path/to/python3.12
./installer/macos/test-setup.sh --skip-build
```

The build creates
`artifacts/Thunderbird-PDF-Archiver-Setup-1.0.1-macos-<architecture>.pkg` and
verifies the XPI, standalone native companion, package domain, native manifest,
and disposable profile install/update behavior. Build Apple silicon and Intel
packages on their respective architectures; PyInstaller one-file executables
cannot be made universal by merging separate builds.

The Windows and macOS builders use their respective checked-in hash locks,
`native-host/requirements.lock` and `native-host/requirements-macos.lock`, because
PyInstaller has different platform dependencies.

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

```text
cd extension
npm ci
npm run typecheck
npm run lint
npm test
npm run package

cd ../native-host
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-macos.lock
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy paperless_mail_archiver tests
.venv/bin/python -m pytest
```

The commands above show the macOS paths. On Windows, use `.venv\Scripts\python.exe`
and the Windows `requirements.lock` instead.

See [architecture](docs/architecture.md), [security](docs/security.md),
[protocol](docs/protocol.md), [testing](docs/testing.md), the
[Slice 3 acceptance contract](docs/slice-3-acceptance.md), and
[troubleshooting](docs/troubleshooting.md). macOS package acceptance is detailed
in [macOS installer testing](docs/macos-installer-testing.md).

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

## License and contributions

Thunderbird PDF Archiver is free and open-source software under the [GNU General Public License Version 3 or later](LICENSE). Forks and modifications are welcome; contributions through [pull requests](CONTRIBUTING.md) are especially encouraged. See the [privacy policy](PRIVACY.md) and [security policy](SECURITY.md) before publication or reporting sensitive issues.
