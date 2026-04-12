#!/bin/bash
set -e

# Collect static files
python manage.py collectstatic --noinput

# Apply database migrations
python manage.py migrate --noinput

# Start the application
exec "$@"