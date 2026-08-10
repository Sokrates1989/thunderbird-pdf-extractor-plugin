# Thunderbird PDF-Archivierung

Diese Thunderbird-128+-Erweiterung speichert genau eine bewusst ausgewählte
E-Mail und ausgewählte unterstützte Anhänge als eine durchsuchbare PDF-Datei in
einem vorhandenen lokalen Ordner. Die Quellnachricht wird weder verschoben noch
markiert oder gelöscht. Ein Paperless-Upload und Zugangsdaten sind nicht Teil
dieses lokalen Arbeitsablaufs.

## Umfang von Slice 2

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

## Bauen und installieren

```powershell
.\installer\windows\build.ps1
.\installer\windows\install.ps1
```

Danach `artifacts\thunderbird-pdf-archiver-0.2.1.xpi` über Thunderbird → Add-ons
und Themes → Erweiterungen → Add-on aus Datei installieren einspielen.
Thunderbird neu starten, in den Einstellungen einen vorhandenen Zielordner über
**Durchsuchen …** auswählen und den lokalen Begleiter testen.

Die Installation erfolgt ohne Administratorrechte unter
`%LOCALAPPDATA%\ThunderbirdPdfArchiver\0.2.1`. LibreOffice ist nur für die
Office-/ODF-Konvertierung erforderlich. Zum Entfernen zuerst die Erweiterung in
Thunderbird löschen und anschließend ausführen:

```powershell
.\installer\windows\uninstall.ps1
```

Erzeugte PDF-Dateien werden bei der Deinstallation nicht gelöscht.
