
# GROBE Installations-Anleitung

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
```