# Testing Slice 2

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
cleanup, and protocol validation. When Chromium exists, a local HTTP canary
proves remote email images are not requested while a CID fixture proves verified
image data can be printed.

The representative merged fixture must also be rendered to PNG with Poppler and
all pages inspected after PDF-affecting changes. Automated service tests do not
replace a real Thunderbird run.

## Slice 2 acceptance walkthrough

Test separately on Thunderbird 128 ESR, the current ESR, and current release:

1. Build/install both `0.2.2` artifacts and restart Thunderbird.
2. Choose a new empty folder with **Durchsuchen …** and test the companion.
3. Open one email containing, in a known order: PDF, PNG/JPEG/WebP/BMP/TIFF,
   TXT, CSV, HTML, nested EML, ZIP, and an inline signature/logo.
4. Confirm each row shows filename, MIME type, size, support, and checkbox.
   Supported real attachments must be checked; inline and unsupported items must
   be unchecked and disabled. Uncheck one otherwise supported file intentionally.
5. Save with separator pages off. Confirm the first section contains searchable
   email metadata/body and an accurate included/skipped list.
6. Confirm subsequent pages follow MIME order, the source PDF remains searchable
   with its original page size/orientation, raster images retain orientation and
   aspect, text/CSV is searchable, HTML contains no active content, and nested
   EML body/children are included.
7. Inspect the PDF outline: **E-Mail**, every included top-level filename, and
   nested child filenames must navigate to the correct starting pages.
8. Confirm the success view shows page count, included/skipped counts and names,
   output path, and **Zielordner öffnen**.
9. In an HTML newsletter, confirm readable link labels are clickable without a
   printed tracking URL. With placeholder mode selected, confirm a web-backed
   image placeholder is clickable and the viewer exposes the real destination
   before or during navigation according to its own security settings.
10. Enable separator pages, repeat, and verify one separator before every
   attachment section while order/outlines remain correct.
11. With no LibreOffice installed, confirm Office/ODF files are disabled with an
    explicit explanation. On a machine with LibreOffice, confirm those formats
    become selectable and convert without UI or macro prompts.
12. Confirm an empty-user-password PDF is normalized and merged, then select a
    corrupt or password-required PDF and confirm the operation fails with that
    filename and leaves no final/temporary output.
13. Cancel during transfer, conversion, and merge; confirm no output remains.
14. Save twice with the same title and confirm collision numbering.
15. Try multiple selected messages and confirm the extension refuses to choose
    one silently.

Record exact Thunderbird, Windows, Chromium, and LibreOffice versions. Do not
claim this manual matrix until it has actually been performed.
