#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
until uv run python - <<'EOF'
import os, sys, psycopg2
try:
    psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "helios_db"),
        user=os.environ.get("DB_USER", "helios_user"),
        password=os.environ.get("DB_PASSWORD", "password"),
    )
    sys.exit(0)
except Exception:
    sys.exit(1)
EOF
do
    echo "  Database not yet ready – retrying in 2 s..."
    sleep 2
done
echo "PostgreSQL is ready."

if [[ "$3" == "gunicorn" ]]; then
    echo "Running database migrations..."
    uv run python manage.py migrate --noinput

    echo "Collecting static files..."
    uv run python manage.py collectstatic --noinput
fi

exec "$@"
