# Native host manifest

`installer/windows/install.ps1` generates the legacy machine-specific manifest
with an absolute executable path. The one-click Inno Setup installer instead
ships `installer/windows/native-manifest.json`, whose executable path is
relative to the installed manifest as supported on Windows. Both installers
register the manifest for the current user. The fixed host name is
`de.sokrates1989.thunderbird_pdf_archiver`; the only allowed extension is
`thunderbird-pdf@felicitas-wisdom.com`.
