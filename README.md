# HfMDK AStA Onlinewahl System

![Logo](static/logo.png)

# HfMDK Wahlsystem

Dieses Projekt ist eine Instanz des Helios Voting Systems, das für die Wahlen an der HfMDK Frankfurt vom AStA eingerichtet wurde. Es ermöglicht sichere, verifizierbare Online-Wahlen.

## Wahlvorgang

Der Wahlvorgang ist in drei Hauptschritte unterteilt, die die Integrität und Verifizierbarkeit der Wahl gewährleisten:

1.  **Stimme abgeben (Cast-as-Intended):**
    Die Wähler*innen erhalten eine Einladung per E-Mail mit einem Link zur Wahlurne.
    Der Stimmzettel wird online ausgefüllt. Die Wahl wird direkt im Browser der Wähler*innen verschlüsselt, sodass nur sie selbst die Klartext-Stimme kennen. Anschließend wird ein Nachweis (Zero-Knowledge Proof) generiert, der belegt, dass die Stimme gültig ist, ohne sie zu offenbaren.

2.  **Stimme aufzeichnen (Recorded-as-Cast):**
    Die verschlüsselte und anonymisierte Stimme wird an den Server gesendet und mit einem individuellen "Ballot Tracker" (Stimmzettel-Hash) versehen. Die Wähler*innen erhalten diesen Hash, um ihre Stimme später in der öffentlichen Liste der Stimmzettel zu finden und zu überprüfen, ob sie korrekt aufgezeichnet wurde. Die Stimmen sind zu diesem Zeitpunkt noch nicht entschlüsselbar.

3.  **Stimme auszählen (Tallied-as-Recorded):**
    Nach Ende der Wahl wird die Auszählung gestartet. Die verschlüsselten Stimmen werden mithilfe der öffentlichen Schlüssel der Trustees entschlüsselt. Jeder Trustee trägt mit seinem geheimen Schlüssel zur Entschlüsselung bei. Erst wenn alle Beiträge kombiniert werden, kann das endgültige Ergebnis berechnet werden. Das Ergebnis kann anschließend von jedem überprüft werden.

## Website zum Laufen bringen

Die Anwendung ist in Python mit dem Django-Framework entwickelt und verwendet Gunicorn sowie Celery für Hintergrundaufgaben.

### Installation und Start

1.  **Abhängigkeiten installieren:**
    ```bash
    # Im Projektverzeichnis
    pip install -r requirements.txt
    ```

2.  **Datenbank konfigurieren:**
    Passe die `.env`-Datei im Hauptverzeichnis an, um die Datenbankverbindung herzustellen. Stelle sicher, dass die Werte für `DB_NAME`, `DB_USER` und `DB_PASSWORD` korrekt sind.

3.  **Datenbank-Migrationen ausführen:**
    ```bash
    python manage.py migrate
    ```

4.  **Statische Dateien sammeln:**
    ```bash
    python manage.py collectstatic
    ```

5.  **Gunicorn und Celery starten:**
    Für den Produktivbetrieb unter Ubuntu/Debian wird die Verwendung von `systemd` empfohlen:
    ```bash
    sudo systemctl start gunicorn
    sudo systemctl start helios-celery
    ```

### Wichtiger Hinweis zu Celery

Wenn du Änderungen an der `.env`-Datei oder an der Konfiguration vornimmst, die Celery betreffen, musst du den Celery-Dienst neu starten, damit die Änderungen wirksam werden.

```bash
sudo systemctl restart helios-celery
