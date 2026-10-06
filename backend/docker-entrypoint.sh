#!/bin/bash
set -e

# Refuse to start with unsafe production settings (e.g. no shared cache)
python manage.py check --deploy --fail-level ERROR

# Collect static files
python manage.py collectstatic --noinput

# Apply database migrations
python manage.py migrate --noinput

# Start the application
exec "$@"