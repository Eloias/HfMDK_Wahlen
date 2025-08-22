# Admin-Docs – HfMDK Online-Wahlen

Diese Datei richtet sich an Administrator:innen der Wahlplattform. Sie liefert einen kompakten Überblick über Aufbau, Betrieb, Sicherheit und das kryptographische Verfahren (basierend auf dem Helios‑Prinzip).

## Anleitung für die [Durchführung der Wahl](Admin-Wahl-Anleitung.md)

---

## 1. Gesamtarchitektur (Überblick)

```
Client (Browser)
   │  HTTPS (TLS)
   ▼
Nginx (Reverse Proxy, SSL-Termination, Static Assets, Rate Limits)
   │  Proxy (Unix Socket / 127.0.0.1)
   ▼
Gunicorn (Python WSGI App – Wahlapplikation)
   │
   ├─ Celery Worker (Asynchrone Jobs: E-Mail, Proof-Generierung, Hintergrund-Tasks)
   │
   ├─ Redis (Message Broker / kurze Caches)
   │
   └─ PostgreSQL (Persistente Datenbank: Wahlen, Nutzer, verschl. Stimmzettel, Logs)
```


---

## 2. Rolle der Komponenten

| Komponente      | Aufgabe |
|-----------------|---------|
| Nginx           | TLS, Kompression, Caching statischer Dateien, Weiterleitung an Gunicorn, Schutz (Rate-Limits, Header-Härtung) |
| Gunicorn        | Ausführen der Python‑WSGI Anwendung (synchroner Teil) |
| Celery Worker   | CPU/zeitintensive Aufgaben (Re-Encryption Mix, Proof-Generierung, Massen-E-Mails) auslagern |
| Celery Beat     | Geplante Jobs (Ablauf von Wahlphasen, Bereinigungen) |
| Redis           | Broker für Celery + kurzer Cache (z.B. Session / Locking) |
| PostgreSQL      | Persistente Daten (Elections, Users, Ballots, Audit-Artefakte) |
| Fail2Ban        | Erkennung & Sperre verdächtiger IPs (SSH, Nginx, evtl. Admin-Login) |
| Firewall (ufw/iptables) | Freigabe nur notwendiger Ports (80→Redirect, 443, SSH eingeschränkt) |
| Systemd         | Prozesskontrolle / Restart-Strategien / Logging |

---

## 3. Verzeichnisstruktur

> Die tatsächliche Struktur kann leicht abweichen!

```
```text
./
├── Admin-Anleitung.md                # Diese Administrations-Dokumentation
├── build-helios-main-site-js.txt     # Build-/Kompilationsprotokoll für Haupt-JS Bundle
├── check_email_env.py                # Prüft Mail-bezogene Umgebungsvariablen
├── check_env.py                      # Allgemeiner Environment-/Konfig-Check
├── CONTRIBUTORS.txt                  # Contributors / Herkunftsinformation
├── deploy-staging.sh                 # Deployment-Skript (Staging Automatisierung)
├── email_debug.py                    # Testversand / Debugging für E-Mail
├── email_import/                     # Modul für E-Mail basierten Import/Verarbeitung
│   ├── README.md                     # Modul-spezifische Hinweise
│   ├── templates/                    # Templates für Mail-Verarbeitung / UI
│   ├── test_email_processing.py      # Tests der Mail-Verarbeitungslogik
│   ├── urls.py / views.py            # Django URL-Routing + Views (Import-Workflow)
├── extract-passwords-for-email.py    # Skript: Export initialer Passwörter (Batch-Mail)
├── gunicorn.sock                     # Unix Socket (Laufzeit – NICHT versionieren!)
├── helios/                           # Kernapplikation (angepasster Helios-Code)
│   ├── apps.py                       # Django AppConfig
│   ├── celery_app.py                 # Celery Initialisierung
│   ├── counters.py                   # (Evtl.) Zähl-/Statistikfunktionen
│   ├── crypto/                       # Kryptomodul (ElGamal, Mix, Proofs)
│   ├── datatypes/                    # Zusätzliche Strukturen / Serialisierungen
│   ├── datetimewidget.py             # UI-Widget für Datums-/Zeitfelder
│   ├── election_url_names.py         # Namenskonstanten (Reverse URL Mapping)
│   ├── election_urls.py              # Separate URL-Konfiguration für Wahlbereiche
│   ├── fields.py / forms.py          # Angepasste Django Felder & Formulare
│   ├── fixtures/                     # Beispiel/Testdaten
│   ├── management/                   # Django Management Commands
│   ├── media/                        # (Falls genutzt) Uploads / generierte Dateien
│   ├── migrations/                   # DB-Schema-Migrationen
│   ├── models.py                     # Zentrale Datenmodelle (Elections, Ballots, etc.)
│   ├── security.py                   # Sicherheits-/Validierungslogik (z.B. Hashes)
│   ├── signals.py                    # Django Signals (z.B. Post-Save Hooks)
│   ├── static/                       # App-lokale statische Dateien
│   ├── stats_* / stats_views.py      # Statistiken / Auswertungen
│   ├── tasks.py                      # Celery Tasks (Proof-Gen, E-Mails, Berechnungen)
│   ├── templates/                    # Jinja/Django Templates (Server-UI)
│   ├── tests.py / test.py            # Tests (ggf. Alt- und Neuformat)
│   ├── url_names.py / urls.py        # Allgemeine URL-Konstanten + Routing
│   ├── utils.py / view_utils.py      # Hilfsfunktionen
│   ├── widgets.py                    # Form-/UI Widgets
│   └── workflows/                   # Prozess-/Phasenlogik (z.B. Wahlphasen)
├── helios_auth/                      # Authentifizierungs-Subsystem
│   ├── auth_systems/                 # Externe / modulare Auth-Provider
│   ├── jsonfield.py                  # Eigene JSON-Feld-Implementierung (Kompat.)
│   ├── security/                     # Auth-spezifische Sicherheitslogik
│   ├── static/ templates/            # Auth-bezogene Assets/UI
│   ├── models.py / views.py / urls.py# Benutzer- & Login-Flows
│   └── utils.py / view_utils.py      # Helper für Auth
├── heliosbooth/                      # Clientseitige Wahlkabine (Browser)
│   ├── boothworker-single.js         # Web Worker für Verschlüsselung (Single)
│   ├── build-helios-booth-compressed.txt # Build-Protokoll Booth JS
│   ├── election.json                 # Beispiel/Cache Wahlparameter
│   ├── verifier.js / verifierworker.js# Lokale Verifikation von Ballots
│   ├── single-ballot-verify.html     # Einzelnachprüfung UI
│   └── vote.html                     # Hauptwahl-Frontend
├── heliosverifier/                   # Externe Verifikationsoberfläche (Auditing)
│   ├── verify.html                   # Audit-Webseite
├── INSTALL.md                        # Installationsanleitung / Setup-Hinweise
├── LICENSE                           # Lizenz
├── manage.py                         # Django Management Entry Point
├── migrate-to-3.5.*                  # Notes/SQL für Versionsmigration (Upstream Sync)
├── Procfile                          # Heroku/Proc-orientierte Prozessdefinition
├── README.md                         # Projekt-Übersicht (Endnutzer/Dev)
├── requirements.txt                  # Python-Abhängigkeiten (Pinned/Constraints)
├── reset.sh                          # Reset-/Neuinitialisierungsskript (Vorsicht!)
├── runtime.txt                       # Plattform Runtime (z.B. Heroku Python-Version)
├── selenium/                        # Ende-zu-Ende Tests (Browser Autom.)
│   └── create-election-and-vote      # Testskripte/Flows
├── server_ui/                        # (Alternative oder ältere) Server UI Komponenten
│   ├── glue.py                       # Verbindungslogik / Aggregation
│   ├── templates/ media/             # UI & statische Ressourcen
│   ├── views.py / urls.py            # Zusätzliche Views/Routes
│   └── view_utils.py                 # UI-Helfer
├── settings.py                       # Zentrale Django Settings (Monolithisch)
├── static/                           # Globale statische Dateien (kompilierte Bundles)
│   ├── *helios-booth-compressed.js   # Gebaute Booth Bundles (Versioniert)
│   ├── jscrypto/                     # JS Kryptographie (ElGamal etc.)
│   ├── booth.css / main.css / style.css # Stylesheets
│   ├── jquery-*.min.js / underscore* # Legacy JS Libs (Auditierbarkeit beachten)
│   ├── logos / Medien / Icons        # Brand Assets
│   └── static_templates/             # Statische Template-Fragmente
├── templates/
│   ├── 404.html / 500.html           # Fehlerseiten (global)
├── urls.py                           # Projektweite Root-URL Konfiguration
├── venv/                             # Virtuelle Python Umgebung (nicht committen empfohlen)
├── wsgi.py                           # WSGI Entry Point (Gunicorn lädt diese Datei)
└── (pycache-Verzeichnisse)           # Bytecode (ignorieren/aufräumen)
```


## 6. Sicherheitshärtung (Auszug)

- Firewall: Nur 22 (eingeschränkt IP), 80 (Weiterleitung), 443 offen.
- SSH: Key-basierte Auth., `PasswordAuthentication no`, `PermitRootLogin no`.
- Fail2Ban Jails: `sshd`, `nginx-http-auth`.
- HTTP Security Header per Nginx:
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
  - `Content-Security-Policy` (angepasst, Skriptquellen minimieren)
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
- Logs: Trennung von Anwendungs- und Audit-Logs (kein Klartext sensibler Daten).
- Secrets: `.env` / systemd Environment, kein Commit.

---

## 7. Kryptographie & Verifizierbarkeit (Kurzfassung Helios-Prinzip)

Die Plattform nutzt (analog Helios):

1. **Ballot Preparation (Clientseitig):**  
   - Der Browser lädt Wahlparameter (inkl. öffentlichem ElGamal-Schlüssel).  
   - Auswahl der Kandidat:innen wird lokal gehalten, dann verschlüsselt (ElGamal, probabilistisch mit frischer Randomness).

2. **Auditierbarkeit vor dem Cast:**  
   - Nutzer:in kann einen erzeugten verschlüsselten Stimmzettel auditieren: Offenlegung von Zufallswerten + Plaintext → Verifikation, dass Ciphertext korrekt ist. Danach wird ein neuer (anderer) Ciphertext erzeugt (gleiche Wahl, neue Randomness).

3. **Casting:**  
   - Versiegelter (sealed) Ciphertext wird mit Authentifizierung zum Server gesendet.
   - Server speichert Ciphertext auf Bulletin Board / DB (unveränderlich protokolliert).

4. **Öffentliche Nachprüfbarkeit:**  
   - Alle verschlüsselten Stimmen (ohne Zuordnung zu IP/Metadaten) sind prüfbar (Hash/ID).
   - Re-Encryption Mix (Permutation + Neu-Verschlüsselung) zur Anonymisierung.  
     - Verwendet „Shadow-Mix“ / Challenge-basierten Beweis (Fiat–Shamir transformiert → nicht-interaktiv).
   - Nach Mix: Chaum–Pedersen Gleichheitsbeweise für jede Entschlüsselung (zeigt Korrektheit ohne Klartext-Schlüssel-Offenlegung).

5. **Tally:**  
   - Nach erfolgreicher Prüfphase werden entschlüsselte Stimmen gezählt.  
   - Beweise + Datenpaket können extern neu geprüft werden (Unabhängige Auditor:innen).

6. **Vertrauensmodell:**  
   - Integrität: kryptographisch absicherbar, selbst bei kompromittiertem Server (Manipulationen an Shuffle/Decrypt würden auffallen).  
   - Vertraulichkeit: schwächer – privater Schlüssel / Trustee auf Server → muss vertrauenswürdig sein. (Mehrere Trustees / Threshold Crypto wäre Erweiterungsmöglichkeit.)

7. **Coercion (Zwang):**  
   - Kein Resistenz-Anspruch (niedriges Risiko-Szenario: Hochschul-/Vereinswahlen).
   - Audit-Mechanismen bewusst so gestaltet, dass Integrität Priorität hat.
---

## 14. Referenzen

- Helios Prinzip / Open-Audit Voting
- Chaum-Pedersen Proofs (Diskrete Log Gleichheit)
- Mixnet / Re-Encryption (Shadow-Mix / Fiat–Shamir)
- PostgreSQL / Redis / Celery / Gunicorn / Nginx Standard-Dokumentation

---


Viel Erfolg beim sicheren Betrieb der HfMDK-Wahlen!