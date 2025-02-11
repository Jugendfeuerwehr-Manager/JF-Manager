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
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    libpcre3 \
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

# Create non-root user and group
RUN groupadd -g 2000 django_group && useradd -m -u 1000 -g django_group django
RUN mkdir -p /etc/uwsgi/apps-enabled
WORKDIR /app

# Create required directories
RUN mkdir -p /static /uploads /tmp/django_imagefit \
    && chown -R django:django_group /app /static /uploads /tmp/django_imagefit

# Copy application code
COPY --chown=django:django . .

# Copy uwsgi.ini to the correct location
COPY --chown=django:django uwsgi.ini /etc/uwsgi/apps-enabled/uwsgi.ini

ENV DJANGO_SETTINGS_MODULE=jf_manager_backend.docker_settings

# Set environment variables for static files
ENV STATIC_ROOT=/static \
    STATIC_URL=/static/ \
    MEDIA_ROOT=/uploads \
    MEDIA_URL=/uploads/

# Switch to non-root user
USER django

# Note: Static files should be collected during deployment.
# Example: docker-compose exec web python manage.py collectstatic --noinput

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8000/health/ || exit 1

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uwsgi", "--ini", "/etc/uwsgi/apps-enabled/uwsgi.ini"]
