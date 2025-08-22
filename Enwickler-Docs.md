
# Installation und Start (für Entwickler)

- installiere PostgreSQL 9.5+
- installiere Rabbit MQ
  Dies wird benötigt, damit Celery funktioniert, das für Hintergrundprozesse wie die Verarbeitung von hochgeladenen CSV-Dateien mit Wählerlisten zuständig ist.
- stelle sicher, dass `virtualenv` installiert ist:
  http://www.virtualenv.org/en/latest/
- clone das repo
- wechsle in das Verzeichnis
- installiere Python 3.6, einschließlich dev, pip und venv
```
sudo apt install python3.6 python3.6-venv python3.6-pip python3.6-venv
```
- erstelle eine virtuelle Umgebung
```
python3.6 -m venv $(pwd)/venv
```
- du benötigst außerdem die Postgres-Entwicklungsbibliotheken. Zum Beispiel unter Ubuntu:
```
sudo apt install libpq-dev
```
- aktiviere die virtuelle Umgebung
```
source venv/bin/activate
```
- installiere die requirements
```
# Im Projektverzeichnis
pip install -r requirements.txt
```
- setze die Datenbank zurück
```
./reset.sh
```
- starte den Server
```
python manage.py runserver
```
- um die Google-Authentifizierung zum Laufen zu bringen:
** gehe zu https://console.developers.google.com
** erstelle eine Anwendung
** richte OAuth2-Anmeldedaten als Webanwendung ein, mit deinem Ursprung, z.B. https://myhelios.example.com, und deinem Authentifizierungs-Rückruf, der, basierend auf unserem Beispiel, https://myhelios.example.com/auth/after/ ist
** immer noch in der Entwicklerkonsole, aktiviere die Google+ API und Google People API.
** setze die Konfigurationsvariablen GOOGLE_CLIENT_ID und GOOGLE_CLIENT_SECRET entsprechend.


2.  **Datenbank konfigurieren:**
    Passe die `.env`-Datei und `settings.py` (Environment Variablen) im Hauptverzeichnis an, um die Datenbankverbindung herzustellen. Darin werden außerdem die Email Server Daten gespeichert.

3.  **Datenbank-Migrationen ausführen:**
    ```bash
    python manage.py migrate
    ```

4.  **Statische Dateien für Website sammeln:**
    ```bash
    python manage.py collectstatic
    ```

5.  **Gunicorn und Celery starten:**
    Für den Produktivbetrieb unter Ubuntu/Debian wird die Verwendung von `systemd` empfohlen:
    ```bash
    sudo systemctl start gunicorn
    sudo systemctl start nginx
    sudo systemctl start helios-celery
    ```

### Wichtiger Hinweis zu Celery

Wenn du Änderungen an der `.env`-Datei oder an der Konfiguration vornimmst, die Celery betreffen, musst du den Celery-Dienst neu starten, damit die Änderungen wirksam werden.

```bash
sudo systemctl restart helios-celery
