import os
print("--- Umgebungsvariablen aus Gunicorn/Celery-Kontext ---")
print(f"EMAIL_HOST_USER: {os.environ.get('EMAIL_HOST_USER')}")
print(f"EMAIL_HOST_PASSWORD: {os.environ.get('EMAIL_HOST_PASSWORD')}")
print("-----------------------------------------------------")
