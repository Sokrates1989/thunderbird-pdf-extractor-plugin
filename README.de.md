# Thunderbird PDF-Archivierung

Diese Thunderbird-128+-Erweiterung speichert genau eine bewusst ausgewählte
E-Mail und ausgewählte unterstützte Anhänge als eine durchsuchbare PDF-Datei in
einem vorhandenen lokalen Ordner. Die Quellnachricht wird weder verschoben noch
markiert oder gelöscht. Ein Paperless-Upload und Zugangsdaten sind nicht Teil
dieses lokalen Arbeitsablaufs.

## Umfang von Release 0.3.0

Der Prüfdialog zeigt Dateiname, MIME-Typ, Größe, Unterstützung und Auswahlstatus
aller erkannten Elemente. Unterstützte echte Anhänge sind vorausgewählt.
Inline-Bilder und nicht unterstützte Dateien sind deaktiviert und werden
ausgelassen. Sowohl der E-Mail-Abschnitt der PDF als auch der Ergebnisdialog
nennen enthaltene und ausgelassene Dateien.

Zusammengeführt werden in ursprünglicher MIME-Reihenfolge:

1. der durchsuchbare E-Mail-Inhalt;
2. PDF-Anhänge ohne Rasterung, einschließlich Dateien, die sich nach sicherer
   Entschlüsselung mit leerem Benutzerkennwort öffnen lassen;
3. PNG, JPEG, WebP, BMP sowie ein- oder mehrseitige TIFF-Bilder;
4. TXT und CSV als durchsuchbarer Text;
5. bereinigtes HTML über denselben lokalen Renderer;
6. verschachtelte EML-Dateien bis zu einer begrenzten Tiefe; und
7. DOCX, XLSX, PPTX, ODT, ODS und ODP, wenn LibreOffice lokal installiert ist.

ZIP/Archive und unbekannte Formate werden nicht entpackt, sondern sichtbar
ausgelassen. Optionale Trennseiten sind standardmäßig aus. PDF-Lesezeichen
werden immer für die E-Mail und jeden enthaltenen Anhang angelegt.

Nicht eingebettete Bilder bleiben als klickbare Platzhalter erhalten, wenn eine
sichere Webadresse oder ein umschließender Weblink vorhanden ist. Lesbare
Linktexte bleiben erhalten, ohne lange Tracking-Adressen daneben auszudrucken.

Release 0.3.0 ergänzt eine redigierte lokale Diagnose, ein begrenztes rotierendes
JSONL-Protokoll, Versions- und SHA-256-Prüfungen bei der Installation sowie ein
portables Windows-Release-ZIP. Diagnose und Protokoll enthalten keine
E-Mail-Inhalte, Dateinamen, URLs, Anhangsnamen oder lokalen Pfade.

## Bauen und installieren

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\build.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\install.ps1
```

Danach `artifacts\thunderbird-pdf-archiver-0.3.0.xpi` über Thunderbird → Add-ons
und Themes → Erweiterungen → Add-on aus Datei installieren einspielen.
Thunderbird neu starten, in den Einstellungen einen vorhandenen Zielordner über
**Durchsuchen …** auswählen und **Diagnose ausführen** wählen.

Die Installation erfolgt ohne Administratorrechte unter
`%LOCALAPPDATA%\ThunderbirdPdfArchiver\0.3.0`. LibreOffice ist nur für die
Office-/ODF-Konvertierung erforderlich.

Der Build erzeugt zusätzlich
`artifacts\thunderbird-pdf-archiver-0.3.0-windows.zip`. Nach dem Entpacken kann
ein Windows-Benutzer `installer\windows\install.ps1` ausführen und die enthaltene
XPI installieren; Node.js, Python und Administratorrechte werden nicht benötigt.

## Update von einer älteren Slice-Version

Die alte Version vorher nicht deinstallieren. Thunderbird schließen, das neue
Release entpacken,
`powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\install.ps1`
ausführen, anschließend die neue XPI über das vorhandene Add-on installieren
und Thunderbird neu starten.
Durch die feste Add-on-ID bleiben Zielordner, Bildmodus und Trennseiten-Einstellung
erhalten. Der Registry-Eintrag wird erst nach erfolgreicher Versions- und
SHA-256-Prüfung auf den Begleiter 0.3.0 umgestellt.

## PDF-Links im Browser

Die PDF behält ausschließlich sichere `http`-, `https`- und `mailto`-URI-Aktionen.
Für diese Aktionen besitzt das PDF-Format keinen standardisierten Schalter
„neuer Tab“; ein normaler Klick wird vom PDF-Viewer gesteuert. Mit **Strg+Klick**
oder der mittleren Maustaste öffnet der Browser den Link in einem neuen Tab. Die
Erweiterung fügt dafür bewusst weder PDF-JavaScript noch `Launch`-Aktionen ein.

Zum Entfernen zuerst die Erweiterung in Thunderbird löschen und anschließend
ausführen:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\uninstall.ps1
```

Erzeugte PDF-Dateien werden bei der Deinstallation nicht gelöscht.
