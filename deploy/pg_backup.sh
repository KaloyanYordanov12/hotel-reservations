#!/usr/bin/env bash
#
# Nightly backup of the hotel database: gzipped, timestamped, 14 day retention.
# Run as the postgres system user (peer auth, no password needed). Wired up by
# the cron line in docs/backup.md.
#
# IMPORTANT: a dump sitting on the same disk as the database is not a backup, it
# is a second copy of the same failure. The off-box copy is a SEPARATE step with
# a destination you choose. This script deliberately does not pick one. See
# docs/backup.md, "Copy it off the box".

set -euo pipefail

BACKUP_DIR=/var/backups/hotel-reservations
DB_NAME=hotel
RETENTION_DAYS=14

umask 077
mkdir -p "${BACKUP_DIR}"

timestamp=$(date +%Y%m%d-%H%M%S)
outfile="${BACKUP_DIR}/hotel-${timestamp}.sql.gz"

# --no-owner and --no-privileges keep the dump portable, so it can restore into a
# scratch database owned by any role.
pg_dump --no-owner --no-privileges "${DB_NAME}" | gzip -9 > "${outfile}"

# Prune local dumps older than the retention window.
find "${BACKUP_DIR}" -maxdepth 1 -name 'hotel-*.sql.gz' -mtime "+${RETENTION_DAYS}" -delete

echo "wrote ${outfile}"

# OFF-BOX COPY GOES HERE, once you have chosen a destination (see docs/backup.md).
# Leave it commented until then so a half-configured copy cannot fail silently.
# Example, after configuring an rclone remote called "offbox":
#   rclone copy "${outfile}" "offbox:hotel-reservations/"
