#!/bin/bash
set -e

# Refuse to start with unsafe production settings (e.g. no shared cache)
python manage.py check --deploy --fail-level ERROR

# Collect static files (jfctl turns this off for one-off maintenance commands)
if [ "${DJANGO_COLLECTSTATIC:-on}" = "on" ]; then
    python manage.py collectstatic --noinput
fi

# Apply database migrations. Production installs managed by jfctl set
# DJANGO_MANAGEPY_MIGRATE=off and migrate explicitly after a backup (OPS-04).
if [ "${DJANGO_MANAGEPY_MIGRATE:-on}" = "on" ]; then
    python manage.py migrate --noinput
fi

# Start the application
exec "$@"
