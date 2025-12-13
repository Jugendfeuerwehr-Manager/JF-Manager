#!/bin/sh
set -e

# Configuration
BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz"

# Default retention
BACKUP_KEEP_DAYS=${BACKUP_KEEP_DAYS:-7}
BACKUP_KEEP_WEEKS=${BACKUP_KEEP_WEEKS:-4}
BACKUP_KEEP_MONTHS=${BACKUP_KEEP_MONTHS:-6}

echo "Starting backup at $(date)"
echo "Database: ${POSTGRES_DB}"
echo "Backup file: ${BACKUP_FILE}"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}/daily" "${BACKUP_DIR}/weekly" "${BACKUP_DIR}/monthly"

# Perform the backup
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h db \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    --no-owner \
    --no-acl \
    | gzip > "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo "✓ Backup created successfully: ${BACKUP_FILE}"
    
    # Copy to daily backups
    cp "${BACKUP_FILE}" "${BACKUP_DIR}/daily/backup_${TIMESTAMP}.sql.gz"
    
    # Weekly backup (Sunday)
    if [ "$(date +%u)" -eq 7 ]; then
        echo "Creating weekly backup..."
        cp "${BACKUP_FILE}" "${BACKUP_DIR}/weekly/backup_${TIMESTAMP}.sql.gz"
    fi
    
    # Monthly backup (1st day of month)
    if [ "$(date +%d)" -eq 01 ]; then
        echo "Creating monthly backup..."
        cp "${BACKUP_FILE}" "${BACKUP_DIR}/monthly/backup_${TIMESTAMP}.sql.gz"
    fi
    
    # Clean up old backups
    echo "Cleaning up old backups..."
    
    # Daily backups - keep last N days
    find "${BACKUP_DIR}/daily" -name "backup_*.sql.gz" -mtime +${BACKUP_KEEP_DAYS} -delete
    
    # Weekly backups - keep last N weeks
    find "${BACKUP_DIR}/weekly" -name "backup_*.sql.gz" -mtime +$((BACKUP_KEEP_WEEKS * 7)) -delete
    
    # Monthly backups - keep last N months
    find "${BACKUP_DIR}/monthly" -name "backup_*.sql.gz" -mtime +$((BACKUP_KEEP_MONTHS * 30)) -delete
    
    # Clean up root backups older than 1 day
    find "${BACKUP_DIR}" -maxdepth 1 -name "backup_*.sql.gz" -mtime +1 -delete
    
    echo "✓ Backup completed successfully at $(date)"
    echo "Backup size: $(du -h ${BACKUP_FILE} | cut -f1)"
else
    echo "✗ Backup failed!"
    exit 1
fi
