#!/bin/sh
set -eu
FILE=${1:-}
[ -f "$FILE" ] || { echo "Usage: $0 backups/file.sql.gz"; exit 1; }
docker compose stop web
docker compose exec -T db dropdb -U "${POSTGRES_USER:-ddc5i}" --if-exists "${POSTGRES_DB:-ddc5i_portfolio}"
docker compose exec -T db createdb -U "${POSTGRES_USER:-ddc5i}" "${POSTGRES_DB:-ddc5i_portfolio}"
gzip -dc "$FILE" | docker compose exec -T db psql -U "${POSTGRES_USER:-ddc5i}" "${POSTGRES_DB:-ddc5i_portfolio}"
docker compose start web
echo "Restore complete."
