#!/usr/bin/env sh
set -eu

BACKUP_ROOT=${BACKUP_ROOT:-/var/backups/praello-ai}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DEST="$BACKUP_ROOT/$STAMP"
mkdir -p "$DEST"

: "${POSTGRES_HOST:=postgres}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_USER:=enterprise_ai}"
: "${POSTGRES_DB:=enterprise_ai}"
: "${PGPASSWORD:?PGPASSWORD must be set}"

pg_dump --host "$POSTGRES_HOST" --port "$POSTGRES_PORT" --username "$POSTGRES_USER" --format custom --file "$DEST/postgres.dump" "$POSTGRES_DB"

QDRANT_URL=${QDRANT_URL:-http://qdrant:6333}
curl --fail --silent --show-error -X POST "$QDRANT_URL/collections/${QDRANT_COLLECTION:-enterprise_knowledge}/snapshots" > "$DEST/qdrant-snapshot.json"

if [ -d "${UPLOAD_DIR:-/app/uploads}" ]; then
  tar -C "${UPLOAD_DIR:-/app/uploads}" -czf "$DEST/uploads.tar.gz" .
fi

if [ "${STORAGE_BACKEND:-local}" = "s3" ]; then
  : "${S3_BUCKET:?S3_BUCKET must be set for object storage backups}"
  aws s3 sync "${S3_BACKUP_SOURCE:-s3://$S3_BUCKET}" "s3://${S3_BACKUP_BUCKET:-$S3_BUCKET-backups}/$STAMP/" --only-show-errors
fi

find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime +"${BACKUP_RETENTION_DAYS:-30}" -exec rm -rf {} +
printf '%s\n' "$DEST"
