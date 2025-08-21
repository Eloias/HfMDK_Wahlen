# E-Mail-Import-Tool für Helios

## Übersicht

Das E-Mail-Import-Tool ist eine neue Funktion für das Helios-Wahlsystem, die es Administratoren ermöglicht, studentische E-Mail-Adressen aus einer Textdatei zu importieren und in ein Helios-kompatibles Format zu konvertieren.

## Funktionalitäten

### Dateiupload
- Upload von `.txt` Dateien über eine Weboberfläche
- Unterstützung für kommagetrennte E-Mail-Adressen
- Validierung des korrekten E-Mail-Formats

### Datenverarbeitung
- **Eingabeformat**: `vorname.nachname@students.hfmdk-frankfurt.de`
- **Ausgabeformat**: `password,Vorname,vorname.nachname@students.hfmdk-frankfurt.de,Vorname Nachname`
- Automatische Extraktion von Vor- und Nachnamen
- Korrekte Großschreibung der Namen

### Dateidownload
- Automatischer Download der konvertierten Datei als CSV
- Dateiname: `helios_voters.csv`

## Technische Implementierung

### Dateistruktur
```
email_import/
├── __init__.py
├── views.py              # Hauptlogik für Upload, Verarbeitung und Download
├── urls.py               # URL-Routing
└── templates/
    └── email_import/
        └── home.html     # Benutzeroberfläche
```

### Integration
- Neuer Link in der Admin-Oberfläche (`/stats/`)
- URL: `/helios/email-import/`
- Erreichbar über "E-Mail-Import-Tool für Helios" in der Admin-Navigation

### Validierung
Das Tool validiert alle E-Mail-Adressen und ignoriert ungültige Einträge:
- Falsche Domain (nicht `@students.hfmdk-frankfurt.de`)
- Fehlendes Punkt im lokalen Teil (nicht `vorname.nachname`)
- Mehrere Punkte im lokalen Teil (z.B. `max.von.mustermann`)

## Beispiel

### Eingabe (sample_emails.txt):
```
max.mustermann@students.hfmdk-frankfurt.de, anna.schmidt@students.hfmdk-frankfurt.de, tim.weber@students.hfmdk-frankfurt.de
```

### Ausgabe (helios_voters.csv):
```
password,Max,max.mustermann@students.hfmdk-frankfurt.de,Max Mustermann
password,Anna,anna.schmidt@students.hfmdk-frankfurt.de,Anna Schmidt
password,Tim,tim.weber@students.hfmdk-frankfurt.de,Tim Weber
```

## Nutzung

1. Als Administrator im Helios-System anmelden
2. Zur Admin-Seite navigieren (`/helios/stats/`)
3. "E-Mail-Import-Tool für Helios" anklicken
4. Textdatei mit E-Mail-Adressen hochladen
5. Konvertierte CSV-Datei wird automatisch heruntergeladen
6. CSV-Datei kann in das bestehende Helios Wähler-Upload-System importiert werden

## Sicherheit

- Nur für Administratoren zugänglich
- Validierung aller Eingaben
- Kein permanenter Speicher von Dateien
- Direkte Verarbeitung und Download