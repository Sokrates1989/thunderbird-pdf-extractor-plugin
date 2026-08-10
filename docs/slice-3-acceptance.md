# Slice 3 acceptance contract

Slice 3 is the Windows packaging and release-hardening gate for version 0.3.0.
It is accepted only when the automated checks pass and the manual Windows /
Thunderbird matrix below has been recorded.

## Implemented release contract

- the XPI and native executable report the same component version;
- the installer verifies the executable version and copied SHA-256 before
  repointing the per-user native-host registry entry;
- the portable release ZIP contains the XPI, executable, install/uninstall
  scripts, notices, and operator documentation;
- updates reuse the fixed add-on ID and preserve extension settings;
- uninstall removes the registry entry, installed host versions, and diagnostic
  logs while leaving every exported PDF untouched;
- progress, cancellation, size/time/page limits, temporary cleanup, and
  collision-safe no-replace output remain enforced;
- the settings page exposes a path-free readiness snapshot;
- the rotating JSONL audit trail accepts only allow-listed tokens and never mail
  content, filenames, attachment names, URLs, local paths, or exception text;
- safe PDF URI links remain clickable, while new-tab behavior stays under the
  browser viewer. Ctrl+click and middle-click are the supported new-tab gestures.

## Automated gate

Run the commands in [testing.md](testing.md), build the release ZIP, inspect its
contents, execute the packaged host `--version` check, parse the PowerShell
scripts, and run installer/uninstaller `-WhatIf` smoke tests. A representative
merged PDF must be rendered with Poppler and every page inspected after any
PDF-affecting change.

## Manual gate

On a clean Windows 11 user account without Python, Node.js, or administrator
rights:

1. Extract `thunderbird-pdf-archiver-0.3.0-windows.zip` and run
   `powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\install.ps1`.
2. Install the included XPI, restart Thunderbird, choose an existing destination,
   and confirm **Run diagnostics** reports matching versions, a standalone EXE,
   Windows runtime, available logging, and a writable output folder.
3. Export the representative Slice 2 fixture and repeat its ordering, attachment,
   image, link, collision, cancellation, and cleanup checks.
4. Confirm Ctrl+click and middle-click on a retained link open a new browser tab.
   Record the normal-click behavior separately because it is viewer-controlled.
5. Install 0.3.0 over the previous version without uninstalling. Confirm output
   folder, image mode, and separator preference remain unchanged and export again.
6. Uninstall the extension and run `uninstall.ps1`. Confirm the host/registry/logs
   are removed and previously exported PDFs remain.
7. Drag the resulting merged PDF into Paperless-ngx and confirm normal ingestion.

Repeat the extension workflow on Thunderbird 128 ESR, current ESR, and current
release. Record exact Thunderbird, Windows, Chromium, and LibreOffice versions;
do not claim this matrix until it has actually been performed.
