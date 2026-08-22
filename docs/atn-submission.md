# Thunderbird Add-ons submission sheet

This document contains copy-ready listing and reviewer information for the
first public submission of PDF Archiver for Thunderbird 1.1.0. Keep it
synchronized with `PRIVACY.md` and the Native Messaging protocol.

Official references:

- [Thunderbird Add-ons review policy](https://thunderbird.github.io/atn-review-policy/)
- [Thunderbird reviewer guide](https://addons-reviewer-guide.thunderbird.net/add-on-review-guide)
- [Source-code submission requirements](https://extensionworkshop.com/documentation/publish/source-code-submission/)

## Listing identity

- Name: `PDF Archiver for Thunderbird`
- Extension ID: `thunderbird-pdf@felicitas-wisdom.com`
- Version: `1.1.0`
- Minimum Thunderbird: `128.0`
- Supported user platforms: Windows 11 and macOS
- Recommended category: `Import/Export`
- Homepage: `https://github.com/Sokrates1989/thunderbird-pdf-extractor-plugin`
- Support: `https://github.com/Sokrates1989/thunderbird-pdf-extractor-plugin/issues`
- License: `GNU General Public License v3.0 or later`

## English listing

### Summary

Save one selected email and supported attachments locally as a searchable PDF.
Requires the separate Windows or macOS companion.

### Description

PDF Archiver for Thunderbird saves one explicitly selected email and selected
supported attachments as a single searchable PDF in an existing local folder.
The review window shows which attachments can be included before anything is
written. The source message is never moved, marked, changed, or deleted.

The Thunderbird Add-ons installation provides the extension only. Before
saving a PDF, install the matching local companion for Windows or macOS using
the download button in the add-on settings. Linux is not currently supported.
The add-on and companion are free and open-source and do not require an online
account.

For an explicit export, the extension transfers the selected raw message,
attachment selection, document title, filename, and processing options through
Thunderbird Native Messaging to the companion installed on the same computer.
The companion parses, converts, merges, and writes the PDF locally. No email,
attachment, generated PDF, filename, output path, credential, or diagnostic is
sent to the maintainer or a conversion service.

Email-body images are placeholders by default. If the user explicitly enables
image embedding, the local companion may request safe HTTPS image URLs once for
that PDF. The image server can then observe the user's IP address and requested
URL. Office and OpenDocument conversion is local and optional and uses an
existing LibreOffice installation.

Open an email and use the message-toolbar button or message context menu to
review and save it. Open the add-on settings to download or diagnose the local
companion, select an existing output folder, choose image handling and separator
preferences, and switch between English and German.

## German listing

### Kurzbeschreibung

Eine ausgewählte E-Mail und unterstützte Anhänge lokal als durchsuchbare PDF
speichern. Benötigt den separaten Windows- oder macOS-Begleiter.

### Beschreibung

PDF Archiver for Thunderbird speichert eine ausdrücklich ausgewählte E-Mail und
ausgewählte unterstützte Anhänge als eine durchsuchbare PDF in einem bestehenden
lokalen Ordner. Vor dem Speichern zeigt der Prüfdialog, welche Anhänge übernommen
werden können. Die ursprüngliche E-Mail wird niemals verschoben, markiert,
verändert oder gelöscht.

Die Installation über Thunderbird Add-ons enthält nur die Erweiterung. Vor dem
ersten PDF-Export muss über die Download-Schaltfläche in den Add-on-Einstellungen
der passende lokale Begleiter für Windows oder macOS installiert werden. Linux
wird derzeit nicht unterstützt. Add-on und Begleiter sind frei und Open Source;
ein Online-Konto ist nicht erforderlich.

Bei einem ausdrücklichen Export überträgt die Erweiterung die ausgewählte rohe
Nachricht, die Anhangsauswahl, Dokumenttitel, Dateiname und Verarbeitungsoptionen
über Thunderbird Native Messaging an den auf demselben Computer installierten
Begleiter. Der Begleiter analysiert, konvertiert, verbindet und speichert die PDF
lokal. E-Mail, Anhänge, erzeugte PDFs, Dateinamen, Zielpfade, Zugangsdaten und
Diagnosen werden weder an den Maintainer noch an einen Konvertierungsdienst
gesendet.

Bilder im Nachrichtentext bleiben standardmäßig Platzhalter. Wird das Einbetten
ausdrücklich aktiviert, kann der lokale Begleiter sichere HTTPS-Bildadressen
einmalig für diese PDF abrufen. Der Bildserver kann dabei IP-Adresse und
angeforderte URL erkennen. Die optionale Office- und OpenDocument-Konvertierung
läuft lokal über eine vorhandene LibreOffice-Installation.

Öffnen Sie eine E-Mail und verwenden Sie die Schaltfläche in der
Nachrichten-Symbolleiste oder das Nachrichten-Kontextmenü. In den Einstellungen
können Begleiter und Diagnose geöffnet, ein bestehender Zielordner ausgewählt,
Bild- und Trennseitenoptionen gewählt sowie Deutsch oder Englisch eingestellt
werden.

## Privacy-policy field

Paste the complete current contents of `PRIVACY.md` into the Thunderbird
Add-ons privacy-policy field. Do not submit only a link. The public description
above summarizes both Native Messaging and optional external image requests.

## Permission explanations

| Permission | Why it is required |
| --- | --- |
| `menus` | Add an explicit Archive as PDF action to supported message context menus. |
| `messagesRead` | Read the one open or selected email and its attachment metadata for the review window and export. |
| `nativeMessaging` | Transfer the explicitly approved message and options to the companion installed on the same computer and receive progress/results. |
| `storage` | Store the selected output folder authorization, language, image behavior, and separator preference locally. |

## Reviewer notes

1. Upload `artifacts/thunderbird-pdf-archiver-1.1.0.xpi` for Windows and macOS.
2. Attach `artifacts/thunderbird-pdf-archiver-1.1.0-atn-source.zip` as source
   code. It includes `ATN_SOURCE_BUILD.md` and pinned npm/Python lock files.
3. The XPI contains generated esbuild output; the source archive reproduces it
   with `npm ci` and `npm run package`.
4. Install the matching 1.1.0 companion from the project's latest GitHub release,
   restart Thunderbird, open add-on Settings, select a disposable output folder,
   and run diagnostics. Extension and companion must both report 1.1.0.
5. Open a synthetic email with a text body and small PDF or image attachment.
   Open the toolbar action, review selections, save the PDF, and verify that the
   source email remains unchanged.
6. The extension sends the raw selected message and approved options only to the
   same-machine companion. There is no maintainer server, telemetry, advertising,
   account, or credential requirement.
7. Keep the default placeholder image mode during the basic test. Optional image
   embedding is the only path that requests remote HTTPS image resources and is
   disclosed in the settings, description, and privacy policy.
8. LibreOffice is optional and needed only to exercise Office/OpenDocument
   attachment conversion.

The native installers are distributed separately from the XPI. Before public
submission, upload the exact companion installers and SHA-256 checksums to the
GitHub release so reviewers and users can verify the binaries.

## Screenshot checklist

Use synthetic email and file names only:

1. review popup showing selected and skipped attachments;
2. successful searchable-PDF result;
3. settings showing the companion requirement, output folder, and diagnostics;
4. German UI variant of the review popup or settings.

Upload screenshots through the dedicated Thunderbird Add-ons screenshot fields.
Do not place external links in the public description; use Homepage and Support
fields and the in-add-on companion button instead.
