# Testing release 1.0.0

## Automated gates

```powershell
Set-Location extension
npm ci
npm run typecheck
npm run lint
npm test
npm run build
npm run package

Set-Location ..\native-host
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy paperless_mail_archiver tests
.\.venv\Scripts\python.exe -m pytest
```

The native suite verifies ordered PDF/image/CSV merging, source PDF text and
page geometry, safe URI-link normalization, active-action removal, metadata,
outlines, nested EML
children, encrypted-PDF failure, unsupported ZIP disclosure, MIME traversal,
cleanup, protocol validation, redacted diagnostic logging, and path-free
readiness reporting. When Chromium exists, a local HTTP canary
proves remote email images are not requested while a CID fixture proves verified
image data can be printed.

Pytest uses the operating system's temporary directory. Do not redirect its
base temporary directory into a protected Documents checkout: the suite creates
and converts harmless Office fixtures, and that rapid file activity can trigger
anti-ransomware heuristics. Chromium-marked tests also require loopback sockets
and a locally launchable browser; record them as environment-blocked when those
capabilities are unavailable.

The representative merged fixture must also be rendered to PNG with Poppler and
all pages inspected after PDF-affecting changes. Automated service tests do not
replace a real Thunderbird run.

The suite also verifies macOS folder selection and Finder opening without shell
parsing, platform diagnostics, and the per-user Application Support audit path.

## Release build gates

From the repository root, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\build.ps1 -SkipDependencyInstall
& .\artifacts\native-host\thunderbird-pdf-archiver-host.exe --version
powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\test-setup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\install.ps1 -WhatIf
powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\uninstall.ps1 -WhatIf
```

The version command must print `1.0.0`. The isolated setup test must complete an
install, existing-profile update, registry check, and uninstall without touching
real Thunderbird state. Inspect
`artifacts\thunderbird-pdf-archiver-1.0.0-windows.zip` and confirm it contains the
one-click setup, 1.0.0 XPI, native executable, legacy install/uninstall scripts,
notices, and Slice 3 operator documents. Parse every PowerShell script and
compile both release and test-mode Inno Setup sources before release. See the
[Windows installer test](windows-installer-testing.md) for the manual gate.

On macOS, run the architecture-native release gate:

```bash
./installer/macos/build-setup.sh --python /path/to/python3.12
./installer/macos/test-setup.sh --skip-build
```

The isolated test must validate the generated Native Messaging manifest,
existing-profile install/update behavior, current-user-only package domain, and
standalone host version without touching the real user profile. Complete the
[macOS installer test](macos-installer-testing.md) before a public Mac release.
The Mac build must install from `native-host/requirements-macos.lock` with hash
checking; the existing Windows build continues to use `requirements.lock`.

## Slice 2 workflow regression walkthrough

Test separately on Thunderbird 128 ESR, the current ESR, and current release:

1. Run Setup once in German and once in English on isolated test profiles.
   Confirm each choice initializes the add-on in the selected language. In the
   settings, switch to the other language and confirm the settings page, archive
   popup, context menu, progress, success, and error messages all change without
   untranslated fallback text.
2. Build/install the matching `1.0.0` extension and companion artifacts and
   restart Thunderbird.
3. Choose a new empty folder with **Durchsuchen …** and run diagnostics. Confirm
   matching component versions, standalone Windows runtime, available audit log,
   renderer/converter status, and a writable output folder without any path in
   the report.
4. Open one email containing, in a known order: PDF, PNG/JPEG/WebP/BMP/TIFF,
   TXT, CSV, HTML, nested EML, ZIP, and an inline signature/logo.
5. Confirm each row shows filename, MIME type, size, support, and checkbox.
   Supported real attachments must be checked; inline and unsupported items must
   be unchecked and disabled. Uncheck one otherwise supported file intentionally.
6. Save with separator pages off. Confirm the first section contains searchable
   email metadata/body and an accurate included/skipped list.
7. Confirm subsequent pages follow MIME order, the source PDF remains searchable
   with its original page size/orientation, raster images retain orientation and
   aspect, text/CSV is searchable, HTML contains no active content, and nested
   EML body/children are included.
8. Inspect the PDF outline: **E-Mail**, every included top-level filename, and
   nested child filenames must navigate to the correct starting pages.
9. Confirm the success view shows page count, included/skipped counts and names,
   output path, and **Zielordner öffnen**.
10. In an HTML newsletter, confirm readable link labels are clickable without a
   printed tracking URL. With placeholder mode selected, confirm a web-backed
   image placeholder is clickable and the viewer exposes the real destination
   before or during navigation according to its own security settings. Confirm
   Ctrl+click and middle-click open a new browser tab; record normal-click
   behavior separately because the PDF viewer controls it.
11. Enable separator pages, repeat, and verify one separator before every
   attachment section while order/outlines remain correct.
12. With no LibreOffice installed, confirm Office/ODF files are disabled with an
    explicit explanation. On a machine with LibreOffice, confirm those formats
    become selectable and convert without UI or macro prompts.
13. Confirm an empty-user-password PDF is normalized and merged, then select a
    corrupt or password-required PDF and confirm the operation fails with that
    filename and leaves no final/temporary output.
14. Cancel during transfer, conversion, and merge; confirm no output remains.
15. Save twice with the same title and confirm collision numbering.
16. Try multiple selected messages and confirm the extension refuses to choose
    one silently.
17. Install Thunderbird AI Assistant 3.0.0, click **Export as PDF** for one
    dashboard message, and confirm this review window opens with exactly that
    message. Disable PDF Archiver and confirm the AI Assistant offers its GitHub
    installation page instead. A request from any other extension ID must not
    open a review window.

Then execute the clean-user, update, uninstall, and Paperless checks in the
[Slice 3 acceptance contract](slice-3-acceptance.md).

Record exact Thunderbird, Windows, Chromium, and LibreOffice versions. Do not
claim this manual matrix until it has actually been performed.
