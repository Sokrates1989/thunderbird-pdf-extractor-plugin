# macOS one-click installer test

The primary macOS artifact is
`Thunderbird-PDF-Archiver-Setup-1.0.0-macos-<architecture>.pkg`. It installs the
extension and local native companion for the current user and does not require
administrator privileges. The Installer shows the bundled GPL-3.0-or-later
terms and requires the operator to acknowledge them before installation. Apple
silicon produces `macos-arm64`; Intel produces `macos-x86_64`.

## Automated isolated test

From the repository root, with Node.js 20.18+ and Python 3.12 available, run:

```bash
./installer/macos/test-setup.sh --python /path/to/python3.12
```

After the initial build, the package-only and postinstall checks can be repeated
without rebuilding:

```bash
./installer/macos/test-setup.sh --skip-build
```

The test uses disposable home, Thunderbird profile, payload, and Native
Messaging directories. It verifies the existing-profile install and update,
the fixed extension ID, the generated absolute native-host path, component
version agreement, localized XPI defaults, the current-user-only package
domain, the Thunderbird close declaration, and the packaged payload. It never
reads or writes a real Thunderbird profile or Mozilla Native Messaging folder.

## Manual acceptance test

Use a disposable macOS user for the clean-install case:

1. Start Thunderbird once so it creates a profile, then close it.
2. Open the package matching the Mac architecture and complete Installer.
3. Start Thunderbird and accept any one-time side-load or permission prompt.
4. Open the add-on settings, select an existing output folder with the native
   macOS picker, and run diagnostics.
5. Confirm the diagnostic reports matching version `1.0.0`, macOS platform,
   standalone executable, redacted audit log, browser/LibreOffice availability,
   and a writable output folder.
6. Export the representative message and inspect the merged PDF.
7. Select **Open output folder** and confirm Finder opens the configured folder.

Then install the same package again and install a newer package over it. Confirm
the add-on remains enabled and its output folder, image mode, separator-page
preference, and language remain unchanged. Confirm an existing profile XPI and
the Native Messaging manifest are updated in place.

Record the exact macOS architecture/version, Thunderbird version, Chrome or
Chromium version, and LibreOffice version. The current package is not Developer
ID-signed or notarized; public distribution requires those release steps.
