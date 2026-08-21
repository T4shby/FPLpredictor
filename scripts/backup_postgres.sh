#!/bin/sh
# Run from the compose host. Writes a custom-format dump beside the repo.
set -e
STAMP=$(date +%Y%m%dT%H%M)
mkdir -p backups
docker compose exec -T postgres pg_dump -U fpl -d fpl -Fc > "backups/fpl_${STAMP}.dump"
find backups -name 'fpl_*.dump' -mtime +7 -delete
echo "backup_completed backups/fpl_${STAMP}.dump"
