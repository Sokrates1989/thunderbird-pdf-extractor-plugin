# Thunderbird PDF Archiver

Diese Thunderbird-128+-Erweiterung speichert genau eine bewusst ausgewählte
E-Mail und ausgewählte unterstützte Anhänge als eine durchsuchbare PDF-Datei in
einem vorhandenen lokalen Ordner. Die Quellnachricht wird weder verschoben noch
markiert oder gelöscht. Ein Paperless-Upload und Zugangsdaten sind nicht Teil
dieses lokalen Arbeitsablaufs.

## Umfang von Release 0.5.0

Das Add-on heißt nun durchgängig **Thunderbird PDF Archiver** und besitzt ein
eigenes PDF-Symbol. Prüfdialog, Einstellungen, Kontextmenü, Prüfmeldungen und
Fehler stehen vollständig auf Deutsch und Englisch zur Verfügung. Der
Windows-Installer fragt nach der anfänglichen Sprache; später kann sie jederzeit
in den Add-on-Einstellungen geändert werden.

Thunderbird AI Assistant 2.9.0 und neuer kann eine ausdrücklich ausgewählte
Dashboard-Mail über eine versionierte Extension-übergreifende Anfrage an dieses
Add-on übergeben. Nur die feste Extension-ID des AI Assistants wird akzeptiert.
Die Anfrage öffnet den normalen Prüfdialog dieses Add-ons; Thunderbird AI
Assistant erhält weder Rohmail, Anhänge, Ausgabepfade, nativen Hostzugriff noch
PDF-Ergebnisse.

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

Release 0.3.0 führte eine redigierte lokale Diagnose, ein begrenztes rotierendes
JSONL-Protokoll, Versions- und SHA-256-Prüfungen bei der Installation sowie ein
portables Windows-Release-ZIP. Diagnose und Protokoll enthalten keine
E-Mail-Inhalte, Dateinamen, URLs, Anhangsnamen oder lokalen Pfade.

## Unter Windows installieren

Lade `Thunderbird-PDF-Archiver-Setup-0.5.0-win-x64.exe` herunter und starte die
Datei. Der benutzerbezogene Installer benötigt keine Administratorrechte. Er
installiert den nativen Begleiter, registriert ihn für 32- und 64-Bit-Thunderbird
und installiert oder aktualisiert die XPI in allen vorhandenen Thunderbird-
Profilen. Auch neue Profile können die registrierte XPI erkennen.

Läuft Thunderbird noch, bittet der Installer um Zustimmung, fordert ein normales
Beenden an, wartet auf mögliche Rückfragen zu offenen Entwürfen und startet
Thunderbird nach der Installation wieder. Thunderbird wird niemals erzwungen
beendet. Bei der ersten Installation kann Thunderbird abschließend einmal um
Bestätigung des seitlich installierten Add-ons bitten. Öffne danach die
Add-on-Einstellungen, wähle den Zielordner und führe die Diagnose aus.

Für ein Update wird die neuere Setup-Datei direkt ausgeführt; vorheriges
Deinstallieren ist nicht nötig. Zum Entfernen dient Windows **Installierte Apps**.
Bereits erzeugte PDF-Dateien werden nicht gelöscht.

Der aktuelle Test-Installer ist noch nicht mit Authenticode signiert. Windows
SmartScreen kann deshalb vor einem unbekannten Herausgeber warnen. Vor dem Start
sollte die veröffentlichte SHA-256-Prüfsumme verglichen werden; ein öffentliches
Release sollte codesigniert werden.

## Bauen

```powershell
winget install --id JRSoftware.InnoSetup --exact
powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\build.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\test-setup.ps1
```

Der Build erzeugt die primäre Installationsdatei unter
`artifacts\Thunderbird-PDF-Archiver-Setup-0.5.0-win-x64.exe`. Der isolierte
Setup-Test verwendet ausschließlich eigene LocalAppData- und Registry-Ziele und
entfernt sie anschließend wieder. Ein echtes Thunderbird-Profil wird nicht
berührt.

Der ältere PowerShell-Installer und die einzelne XPI bleiben für die technische
Fehlersuche erhalten, sind aber nicht mehr der empfohlene Installationsweg.

Setup installiert ohne Administratorrechte unter
`%LOCALAPPDATA%\ThunderbirdPdfArchiver\0.5.0`. LibreOffice ist nur für die
Office-/ODF-Konvertierung erforderlich.

Der Build erzeugt zusätzlich
`artifacts\thunderbird-pdf-archiver-0.5.0-windows.zip`. Nach dem Entpacken kann
ein Windows-Benutzer `installer\windows\install.ps1` ausführen und die enthaltene
XPI installieren; Node.js, Python und Administratorrechte werden nicht benötigt.

## Update von einer älteren Slice-Version

Die alte Version vorher nicht deinstallieren. Führe direkt die Setup-EXE aus. Sie
beendet Thunderbird kontrolliert, aktualisiert eine vorhandene Profil-XPI,
registriert die XPI für neue Profile und startet Thunderbird wieder. Durch die
feste Add-on-ID bleiben Zielordner, Bildmodus, Trennseiten-Einstellung und Sprache
erhalten.

## PDF-Links im Browser

Die PDF behält ausschließlich sichere `http`-, `https`- und `mailto`-URI-Aktionen.
Für diese Aktionen besitzt das PDF-Format keinen standardisierten Schalter
„neuer Tab“; ein normaler Klick wird vom PDF-Viewer gesteuert. Mit **Strg+Klick**
oder der mittleren Maustaste öffnet der Browser den Link in einem neuen Tab. Die
Erweiterung fügt dafür bewusst weder PDF-JavaScript noch `Launch`-Aktionen ein.

Der empfohlene Installer legt einen Eintrag unter Windows **Installierte Apps**
an. Seine Deinstallation entfernt registrierte und profilbezogene XPI-Dateien,
den nativen Begleiter, das Manifest und Diagnoseprotokolle. Die ältere
Entwicklungsinstallation kann weiterhin entfernt werden mit:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\uninstall.ps1
```

Erzeugte PDF-Dateien werden bei der Deinstallation nicht gelöscht.
