#!/usr/bin/env bash
# backup_db.sh (TASK-028) — physical backup of the AGE database in custom
# format plus a checksum manifest, with retention-based pruning.
#
# Required environment:
#   DB_HOST, DB_PORT, DB_NAME, DB_SUPERUSER, PGPASSWORD (or .pgpass)
#   BACKUP_DIR (default ./backups), RETENTION_DAYS (default 7)
#
# Usage:  ./backup_db.sh            (run from cron: 0 */1 * * * for RPO < 1h)

set -euo pipefail

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5433}"
DB_NAME="${DB_NAME:-age_prod_01}"
DB_SUPERUSER="${DB_SUPERUSER:-postgres}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

: "${PGPASSWORD:?PGPASSWORD must be set (read from environment / secret store)}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="$BACKUP_DIR/${DB_NAME}-${STAMP}.dump"

echo "[backup] dumping postgresql://${DB_HOST}:${DB_PORT}/${DB_NAME}"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_SUPERUSER" -d "$DB_NAME" \
    --format=custom --compress=6 --file "$FILE"

SHA256="$(sha256sum "$FILE" | cut -d' ' -f1)"
SIZE="$(du -h "$FILE" | cut -f1)"
cat >> "$BACKUP_DIR/manifest.log" <<EOF
${STAMP}  ${FILE}  sha256=${SHA256}  size=${SIZE}
EOF

echo "[backup] wrote ${FILE} (${SIZE}, sha256=${SHA256})"

# Verify the archive is restorable (TOC readable) before pruning.
pg_restore --list "$FILE" > /dev/null
echo "[backup] archive verified (pg_restore --list OK)"

find "$BACKUP_DIR" -name "${DB_NAME}-*.dump" -mtime +"$RETENTION_DAYS" -delete
echo "[backup] pruned archives older than ${RETENTION_DAYS} days"
