# --- Build stage ---
FROM python:3.11-slim-bookworm AS builder

ARG BUILD_DATE
ARG VCS_REF

LABEL maintainer="info@lukas-bisdorf.de" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.description="JF Manager Backend - Build Stage" \
      org.opencontainers.image.source="https://github.com/Jugendfeuerwehr-Manager/JF-Manager"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir pipenv uwsgi mysqlclient psycopg2-binary

WORKDIR /app

# Copy dependency files
COPY Pipfile Pipfile.lock ./

# Install dependencies
RUN pipenv install --deploy --system && \
    pip uninstall -y pipenv

# --- Final stage ---
FROM python:3.11-slim-bookworm AS production

ARG BUILD_DATE
ARG VCS_REF

LABEL maintainer="info@lukas-bisdorf.de" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.description="JF Manager Backend - Production" \
      org.opencontainers.image.source="https://github.com/Jugendfeuerwehr-Manager/JF-Manager"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=jf_manager_backend.docker_settings \
    STATIC_ROOT=/static \
    STATIC_URL=/static/ \
    MEDIA_ROOT=/uploads \
    MEDIA_URL=/uploads/

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    default-mysql-client \
    libpq5 \
    default-libmysqlclient21 \
    curl \
    && rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user and group
RUN groupadd -g 2000 django_group && \
    useradd -m -u 1000 -g django_group django && \
    mkdir -p /etc/uwsgi/apps-enabled

WORKDIR /app

# Create required directories with proper permissions
RUN mkdir -p /static /uploads /tmp/django_imagefit && \
    chown -R django:django_group /app /static /uploads /tmp/django_imagefit

# Copy application code
COPY --chown=django:django_group . .

# Copy uwsgi.ini to the correct location
COPY --chown=django:django_group uwsgi.ini /etc/uwsgi/apps-enabled/uwsgi.ini

# Make entrypoint executable
RUN chmod +x /app/docker-entrypoint.sh

# Switch to non-root user
USER django

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail http://localhost:8000/health/ || exit 1

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uwsgi", "--ini", "/etc/uwsgi/apps-enabled/uwsgi.ini"]
