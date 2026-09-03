#!/usr/bin/env bash
# restore_db.sh (TASK-028) — restore a backup produced by backup_db.sh.
#
#   ./restore_db.sh backups/age_prod_01-20260903T000000Z.dump [TARGET_DB]
#
# TARGET_DB defaults to the source database name. DANGER: this drops and
# recreates objects in the target database — never point it at production
# without a change record.

set -euo pipefail

DUMP="${1:?usage: restore_db.sh <backup.dump> [target_db]}"
TARGET_DB="${2:-$(basename "$DUMP" | sed -E 's/-[0-9T]+Z?\.dump$//')}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5433}"
DB_SUPERUSER="${DB_SUPERUSER:-postgres}"

: "${PGPASSWORD:?PGPASSWORD must be set (read from environment / secret store)}"

echo "[restore] verifying checksum manifest entry (if present)"
MANIFEST="$(dirname "$DUMP")/manifest.log"
if [ -f "$MANIFEST" ] && grep -F "$(basename "$DUMP")" "$MANIFEST" >/dev/null; then
    EXPECTED="$(grep -F "$(basename "$DUMP")" "$MANIFEST" | tail -1 | sed -E 's/.*sha256=([0-9a-f]+).*/\1/')"
    ACTUAL="$(sha256sum "$DUMP" | cut -d' ' -f1)"
    if [ "$EXPECTED" != "$ACTUAL" ]; then
        echo "[restore] CHECKSUM MISMATCH — refusing to restore" >&2
        exit 1
    fi
    echo "[restore] checksum OK (${ACTUAL:0:16}...)"
fi

echo "[restore] restoring into postgresql://${DB_HOST}:${DB_PORT}/${TARGET_DB}"
read -r -p "This will DROP and recreate objects in '${TARGET_DB}'. Type the database name to confirm: " CONFIRM
[ "$CONFIRM" = "$TARGET_DB" ] || { echo "aborted"; exit 1; }

pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_SUPERUSER" -d "$TARGET_DB" \
    --clean --if-exists --no-owner --no-privileges --jobs=4 "$DUMP"

echo "[restore] done — run the application test suite against the restored DB"
