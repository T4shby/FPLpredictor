# Backup and restore

## Docker / production

Postgres data lives in the `postgres_data` volume. Dump to `./backups` (bind-mounted, outside the data volume):

```bash
docker compose exec postgres pg_dump -U fpl -d fpl -Fc > backups/fpl_$(date +%Y%m%d).dump
```

Keep at least 7 daily dumps. Copy them off the VPS.

## Restore

```bash
docker compose exec -T postgres pg_restore -U fpl -d fpl --clean --if-exists < backups/fpl_YYYYMMDD.dump
```

## Also back up

- `.env` (secrets, not in git)
- `data/snapshots/`
- `config/`

Automated cron for dumps is **TODO** on the VPS until a host crontab or compose sidecar is added.
