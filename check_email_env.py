# check_email_env.py
import os
import sys  # <-- Diese Zeile ist wichtig
import django
from django.conf import settings
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Bestimme den absoluten Pfad zum Projekt-Stammverzeichnis (wo manage.py ist)
# Dies ist notwendig, damit Django die 'helios'-App finden kann
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Stelle sicher, dass die Umgebungsvariable für Django-Settings gesetzt ist
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "helios.settings")

# Initialisiere Django
try:
    django.setup()
except Exception as e:
    print(f"Fehler beim Django-Setup: {e}")
    print("Bitte stelle sicher, dass 'helios.settings' korrekt ist und alle Abhängigkeiten installiert sind.")
    sys.exit(1)


print("--- Django Settings (aus settings.py nach Laden der Umgebungsvariablen) ---")
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
# Zeige nur die ersten paar Zeichen des Passworts aus Sicherheitsgründen
print(f"EMAIL_HOST_PASSWORD (erste 3 Zeichen): {settings.EMAIL_HOST_PASSWORD[:3]}...")
print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}")

print("\n--- Umgebungsvariablen (direkt aus os.environ, die für Gunicorn verfügbar sein sollten) ---")
print(f"OS_EMAIL_HOST: {os.environ.get('EMAIL_HOST', 'NICHT GESETZT')}")
print(f"OS_EMAIL_PORT: {os.environ.get('EMAIL_PORT', 'NICHT GESETZT')}")
print(f"OS_EMAIL_HOST_USER: {os.environ.get('EMAIL_HOST_USER', 'NICHT GESETZT')}")
# Zeige nur die ersten paar Zeichen des Passworts aus Sicherheitsgründen
print(f"OS_EMAIL_HOST_PASSWORD: {os.environ.get('EMAIL_HOST_PASSWORD', 'NICHT GESETZT')[:3]}...")


print("\n--- Test Verbindung (wenn Umgebungsvariablen korrekt sind und die E-Mail senden können) ---")
try:
    # Verwenden der Werte, die Django aus settings.py geladen hat
    test_host = settings.EMAIL_HOST
    test_port = settings.EMAIL_PORT
    test_user = settings.EMAIL_HOST_USER
    test_password = settings.EMAIL_HOST_PASSWORD
    test_use_tls = settings.EMAIL_USE_TLS
    test_use_ssl = settings.EMAIL_USE_SSL

    # Überprüfen auf Standardwerte oder leere Felder
    if not test_user or not test_password or test_host == 'localhost':
        print("E-Mail-Einstellungen scheinen noch Standardwerte oder unvollständig zu sein.")
        print("Überspringe detaillierten SMTP-Verbindungstest.")
    else:
        print(f"Versuche SMTP-Verbindung zu {test_host}:{test_port}...")
        server = None
        if test_use_ssl:
            print("Verwende SMTPS (SMTP over SSL)...")
            server = smtplib.SMTP_SSL(test_host, test_port)
        else:
            print("Verwende SMTP...")
            server = smtplib.SMTP(test_host, test_port)

        with server:
            server.set_debuglevel(1) # Zeigt detaillierte Kommunikation mit dem SMTP-Server

            if test_use_tls and not test_use_ssl:
                print("Starte TLS...")
                server.starttls()
                print("TLS gestartet.")

            print("Versuche Login...")
            server.login(test_user, test_password)
            print("Login erfolgreich!")

            msg = MIMEText('Dies ist eine Testnachricht vom Server, um die finalen E-Mail-Einstellungen zu prüfen.')
            msg['Subject'] = 'Helios Server E-Mail Test - Final und Automatisiert'
            msg['From'] = test_user
            msg['To'] = 'elias.ohly@gmail.com' # <--- WICHTIG: ERSETZE DIES MIT DEINER EIGENEN E-MAIL-ADRESSE FÜR DEN TEST

            print("Sende Test-E-Mail...")
            server.sendmail(test_user, 'elias.ohly@gmail.com', msg.as_string())
            print("Test-E-Mail erfolgreich gesendet!")

except Exception as e:
    print(f"\nFehler bei der SMTP-Verbindung oder beim Senden der E-Mail (ausführlich): {e}")
