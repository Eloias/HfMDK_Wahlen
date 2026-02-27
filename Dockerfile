FROM python:3.13-slim

# Install system dependencies required by python-ldap and psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libldap2-dev \
    libsasl2-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first so Docker can cache the install layer
COPY pyproject.toml uv.lock ./

# Install Python dependencies (no project itself yet, speeds up layer caching)
RUN uv sync --frozen --no-dev --no-install-project

# Copy the rest of the project
COPY . .

# Finalise the install
RUN uv sync --frozen --no-dev

# Create the directory used by STATIC_ROOT in settings.py
RUN mkdir -p /var/www/HfMDK_Wahlen/static

EXPOSE 8000

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uv", "run", "gunicorn", "wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]