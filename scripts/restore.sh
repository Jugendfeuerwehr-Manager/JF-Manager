#!/bin/sh
set -e

# Configuration
BACKUP_DIR="/backups"

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Available backups:"
    find "${BACKUP_DIR}" -name "backup_*.sql.gz" -type f | sort -r | head -20
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Error: Backup file '${BACKUP_FILE}' not found!"
    exit 1
fi

echo "========================================="
echo "WARNING: Database Restore Operation"
echo "========================================="
echo "This will REPLACE the current database with the backup:"
echo "Backup file: ${BACKUP_FILE}"
echo "Database: ${POSTGRES_DB}"
echo "========================================="
echo ""
echo "Press Ctrl+C to cancel, or wait 10 seconds to continue..."
sleep 10

echo ""
echo "Starting restore at $(date)"

# Drop existing connections
echo "Terminating existing connections..."
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h db \
    -U "${POSTGRES_USER}" \
    -d postgres \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();"

# Drop and recreate database
echo "Dropping database..."
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h db \
    -U "${POSTGRES_USER}" \
    -d postgres \
    -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};"

echo "Creating fresh database..."
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h db \
    -U "${POSTGRES_USER}" \
    -d postgres \
    -c "CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};"

# Restore backup
echo "Restoring backup..."
gunzip < "${BACKUP_FILE}" | PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h db \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}"

if [ $? -eq 0 ]; then
    echo "✓ Restore completed successfully at $(date)"
else
    echo "✗ Restore failed!"
    exit 1
fi
