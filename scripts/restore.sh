#!/bin/bash

# Database Restore Script
# Usage: ./scripts/restore.sh <backup_file>

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 backups/kundelik_predict_20240101_120000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "WARNING: This will overwrite the current database!"
read -p "Are you sure you want to restore from $BACKUP_FILE? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo "Stopping application..."
docker-compose stop web

echo "Restoring database from $BACKUP_FILE..."

# Handle both compressed and uncompressed backups
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip -c "$BACKUP_FILE" | docker-compose exec -T db psql -U postgres kundelik_predict
else
    cat "$BACKUP_FILE" | docker-compose exec -T db psql -U postgres kundelik_predict
fi

echo "Starting application..."
docker-compose start web

echo "Database restore completed successfully!"
