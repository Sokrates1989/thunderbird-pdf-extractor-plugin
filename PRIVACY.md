# Privacy Policy

Last updated: 22 August 2026

PDF Archiver for Thunderbird processes one email and the attachments explicitly selected by the user. The extension transfers the selected message source, attachment selection, document title, filename, and processing options through Thunderbird Native Messaging to the companion installed on the same computer. The companion parses and renders that data locally.

The project does not upload email, attachments, generated PDFs, filenames, output paths, credentials, or diagnostics to the maintainer or a conversion service. Optional Office and OpenDocument conversion invokes a locally installed LibreOffice application. Generated PDFs are written only to the existing local folder selected by the user.

External email-body images are represented by placeholders by default. If the user explicitly selects image embedding, the local companion may request safe HTTPS image URLs once while producing that PDF. The remote image server can then observe the user's IP address and the requested URL, which may identify that the message was opened. Unsafe, unavailable, oversized, and non-HTTPS resources remain placeholders.

Settings and the selected output-folder authorization are stored locally. The companion keeps a bounded, redacted local audit log and diagnostic snapshot that exclude email content, filenames, URLs, attachment names, and local paths. Users can remove the installed companion and its local diagnostics through the native uninstaller; generated PDFs are intentionally retained.

Privacy questions can be sent to `thunderbird-pdf@felicitas-wisdom.com` or reported through GitHub Issues without attaching private email or documents.
