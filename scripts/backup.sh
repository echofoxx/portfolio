#!/bin/sh
set -eu
mkdir -p backups
STAMP=$(date +%Y%m%d-%H%M%S)
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-ddc5i}" "${POSTGRES_DB:-ddc5i_portfolio}" | gzip > "backups/ddc5i-${STAMP}.sql.gz"
cp "backups/ddc5i-${STAMP}.sql.gz" backups/latest.sql.gz
echo "Backup written to backups/ddc5i-${STAMP}.sql.gz"
