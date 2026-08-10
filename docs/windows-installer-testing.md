# Windows one-click installer test

The primary Windows artifact is
`Thunderbird-PDF-Archiver-Setup-0.3.0-win-x64.exe`. It installs per user and does
not require administrator privileges.

## Automated isolated test

From the repository root, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\test-setup.ps1
```

The test compiles a dedicated setup whose files and registry entries live below
`%LOCALAPPDATA%\ThunderbirdPdfArchiverInstallerTest` and
`HKCU\Software\ThunderbirdPdfArchiverInstallerTest`. It verifies payload files,
native-host and XPI registrations, an existing-profile XPI update, and complete
uninstallation. The test refuses to reuse a pre-existing target and cleans its
owned state in `finally`. It never closes or starts Thunderbird and never reads
or writes a real Thunderbird profile.

## Manual acceptance test

Use a disposable Windows user or VM for the clean-install case:

1. Start Thunderbird once so it creates a profile, then close it.
2. Run the setup without administrator elevation.
3. Confirm Windows **Installed apps** lists **Thunderbird PDF Archiver**.
4. Start Thunderbird and accept its one-time side-load/permission prompt if it
   appears.
5. Open the add-on settings, select an existing destination, and confirm the
   diagnostic reports matching version `0.3.0`, packaged host, Windows runtime,
   available Chromium renderer, audit log, and writable destination.
6. Export the representative message and inspect the merged PDF.

Then test controlled restart and update:

1. Open Thunderbird and an unsaved compose draft.
2. Start setup again. Confirm it explains the restart and never force-closes the
   process. Respond to Thunderbird's draft prompt and allow setup to continue.
3. Leave **Start Thunderbird now** checked and confirm Thunderbird reopens.
4. Confirm the add-on remains enabled and its output folder, image mode, and
   separator preference remain unchanged.

Finally uninstall through Windows **Installed apps**. Confirm the add-on and
native-host registration disappear after Thunderbird restarts, while exported
PDFs remain untouched.

Record the exact Windows and Thunderbird versions. The unsigned test build may
trigger SmartScreen; a public release requires an Authenticode signing step.
