# --- Build stage ---
FROM python:3.11-slim-bullseye as builder

# Add labels according to Docker best practices
LABEL maintainer="info@lukas-bisdorf.de" \
      org.opencontainers.image.description="JF Manager Server" \
      org.opencontainers.image.source="https://github.com/Jugendfeuerwehr-Manager/JF-Manager"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pipenv uwsgi mysqlclient

WORKDIR /app

# Copy dependency files
COPY Pipfile Pipfile.lock ./

# Install dependencies
RUN pipenv install --deploy --system

# --- Final stage ---
FROM python:3.11-slim-bullseye

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user
RUN useradd -m -u 1000 django

WORKDIR /app

# Create required directories
RUN mkdir -p /static /uploads /tmp/django_imagefit \
    && chown -R django:django /app /static /uploads /tmp/django_imagefit

# Copy application code
COPY --chown=django:django . .

ENV DJANGO_SETTINGS_MODULE=jf_manager_backend.docker_settings

# Switch to non-root user
USER django

# Collect static files
RUN DATABASE_URL=none python manage.py collectstatic --noinput

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8000/health/ || exit 1

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uwsgi", "--ini", "/etc/uwsgi/apps-enabled/uwsgi.ini"]
