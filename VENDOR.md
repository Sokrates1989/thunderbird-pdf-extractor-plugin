# Third-party dependencies

All dependencies are pinned. JavaScript transitive versions are captured in
`extension/package-lock.json`; Python transitive versions and artifact hashes are
captured in `native-host/requirements.lock`.

## Shipped Python runtime libraries

| Package | Version | Purpose | License |
| --- | ---: | --- | --- |
| pypdf | 6.15.0 | PDF validation, page merging, metadata, and outlines | BSD-3-Clause |
| ReportLab | 5.0.0 | Searchable fallback, text, image, and separator PDF rendering | BSD-style |
| Pillow | 12.3.0 | Bounded raster attachment decoding and orientation | HPND |
| charset-normalizer | 3.4.9 | ReportLab transitive text support | MIT |

The standalone Windows executable is produced by PyInstaller 6.22.0. PyInstaller
is build tooling under GPL-2.0-or-later with its exception; it does not impose the
GPL on the bundled application.

## Extension development dependencies

The extension ships bundled first-party JavaScript and static assets. TypeScript,
esbuild, ESLint, typescript-eslint, Vitest, Archiver, and type declarations are
development/build dependencies and are not loaded remotely at runtime. Exact
versions and licenses are recorded in the npm lock file and can be audited with:

```powershell
Set-Location extension
npm query ':root > .prod, :root > .dev'
```

No CDN, remote script, telemetry SDK, conversion service, or copied third-party
source asset is used.
