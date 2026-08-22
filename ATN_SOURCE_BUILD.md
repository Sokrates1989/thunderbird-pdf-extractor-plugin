# Thunderbird Add-ons reviewer build

This source archive corresponds to PDF Archiver for Thunderbird 1.1.0. It
contains the human-readable TypeScript source, native-companion Python source,
installer source, pinned lock files, tests, and documentation used for the
submitted XPI and separately published companion packages.

## XPI build environment

- Linux or macOS;
- Node.js 20.18 or newer;
- npm with lockfile support.

The XPI build uses open-source tools pinned by `extension/package-lock.json`.
The submitted XPI contains generated esbuild output, so this source archive is
attached for reviewer reproduction.

## Build the submitted XPI

From the source-archive root:

```bash
cd extension
npm ci
npm run typecheck
npm run lint
npm test
npm run package
```

The upload candidate is
`artifacts/thunderbird-pdf-archiver-1.1.0.xpi` relative to the source-archive
root. The packaged manifest must report version `1.1.0`, extension ID
`thunderbird-pdf@felicitas-wisdom.com`, and Thunderbird 128.0 or newer.

## Native companion

Thunderbird Add-ons distributes the XPI only. Saving PDFs requires the separate
Windows or macOS companion installer linked from the add-on settings and the
project's latest GitHub release. The extension sends one explicitly selected
message and its selected processing options to that local companion through
Native Messaging. The complete privacy boundary is documented in `PRIVACY.md`.

The companion is not needed to reproduce the XPI. Platform-specific companion
build and disposable installer-test commands are documented in `README.md`,
`docs/macos-installer-testing.md`, and `docs/windows-installer-testing.md`.
