#!/bin/bash

# Database Backup Script
# Usage: ./scripts/backup.sh

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/kundelik_predict_$TIMESTAMP.sql"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "Starting database backup..."

# Backup PostgreSQL database
docker-compose exec -T db pg_dump -U postgres kundelik_predict > "$BACKUP_FILE"

# Compress the backup
gzip "$BACKUP_FILE"
BACKUP_FILE="$BACKUP_FILE.gz"

echo "Backup completed: $BACKUP_FILE"
echo "Backup size: $(du -h "$BACKUP_FILE" | cut -f1)"

# Keep only the last 7 backups
echo "Cleaning up old backups..."
ls -t "$BACKUP_DIR"/*.sql.gz | tail -n +8 | xargs -r rm

echo "Backup process finished successfully!"
