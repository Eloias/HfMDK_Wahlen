import os
import sys
import django
from django.conf import settings

# Django Setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings") # Oder wie dein Projekt heißt, oft 'helios.settings' oder 'server_ui.settings'
django.setup()

print("----- AKTUELLE LIVE EINSTELLUNGEN -----")
print(f"EMAIL_HOST:     {settings.EMAIL_HOST}")
print(f"EMAIL_PORT:     {settings.EMAIL_PORT}")
print(f"EMAIL_USE_TLS:  {settings.EMAIL_USE_TLS} (Typ: {type(settings.EMAIL_USE_TLS)})")
print(f"EMAIL_USER:     {settings.EMAIL_HOST_USER}")
print("---------------------------------------")

# Test Mail senden
from django.core.mail import send_mail
try:
    print("Versuche zu senden...")
    send_mail('Check Settings Test', 'Test', settings.EMAIL_HOST_USER, ['elias.ohly@gmail.com'], fail_silently=False)
    print("ERFOLG! Die Einstellungen stimmen.")
except Exception as e:
    print(f"FEHLER: {e}")
