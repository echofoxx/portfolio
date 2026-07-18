# Upgrade to v0.5.0

This guide upgrades an existing v0.4.0 installation while preserving PostgreSQL and task-file storage volumes.

## 1. Review the change

v0.5.0 adds migration `0005_portfolio_governance_v050` and new records for:

- delegations
- integration connections and field-ownership rules
- synchronization runs
- portfolio reviews and review items
- resource requests
- financial transactions
- scenarios, changes, and results
- data-quality issues
- report packs and job runs

The migration does not delete or rename v0.4.0 demand, project, task, attachment, board, schedule, status-report, audit, or RTM tables.

## 2. Back up before upgrading

From the v0.4.0 project folder:

```bash
docker compose ps
docker compose exec -T db pg_dump \
  -U "${POSTGRES_USER:-ddc5i}" \
  -d "${POSTGRES_DB:-ddc5i_portfolio}" \
  --clean --if-exists | gzip > ddc5i-before-v050.sql.gz
```

Back up the attachment volume as documented in `BACKUP_RESTORE.md`.

## 3. Stop the old release

```bash
docker compose down
```

Do not use `-v`; deleting the named volumes removes the database and uploaded files.

## 4. Replace application source

Extract v0.5.0 into a clean folder. Retain the existing `.env` and named Docker volumes. Compare `.env.example` with the current settings, especially:

```env
PUBLIC_BASE_URL=http://localhost:8080
TRUST_PROXY_HOPS=0
RATE_LIMIT_REQUESTS=300
RATE_LIMIT_WINDOW_SECONDS=900
MAX_UPLOAD_MB=10
```

## 5. Build and start

```bash
docker compose up -d --build
docker compose ps
curl -fsS http://localhost:8080/health/ready
```

The web container runs:

```bash
alembic upgrade head
python -m app.seed
```

Seed execution is idempotent. It adds v0.5.0 demonstration/reference records and synchronizes packaged RTM evidence without replacing user-created business records.

## 6. Verify the migration

```bash
docker compose exec web alembic current
```

Expected head:

```text
0005_portfolio_governance_v050
```

Check logs:

```bash
docker compose logs --tail=200 web db
```

Then verify:

1. Existing users can sign in.
2. Existing demand, project, task, attachment, and status-report records remain present.
3. Administration opens and lists users and delegations.
4. Integrations displays the ProjectOS mock and disabled Microsoft 365/SharePoint connections.
5. Portfolio Reviews, Scenarios, Data Quality, and Operations open for authorized roles.
6. The RTM still contains 307 rows.

## 7. Run regression tests

```bash
docker compose run --rm web pytest -q
```

The release workspace passed 57 tests. Target-host results should be retained as local acceptance evidence.

## Rollback

The safe rollback is database-and-storage restoration, not a blind migration downgrade:

1. Stop v0.5.0.
2. Restore the pre-upgrade PostgreSQL backup and attachment-volume backup.
3. Restore the v0.4.0 source tree and `.env`.
4. Rebuild and verify health.

The migration downgrade removes only v0.5.0 tables, but restoring the backup is preferred because it also restores application data and RTM evidence to a consistent point in time.

## Post-upgrade hardening

- Keep ProjectOS in Mock/Dry Run until endpoint ownership, credentials, network path, idempotency, conflict rules, and reconciliation are approved.
- Do not enter real financial, workforce, or sensitive operational data into a demonstration deployment.
- Review delegations manually; v0.5.0 records them but does not yet apply delegated roles to every authorization check.
- Capture target-host Docker, browser, reverse-proxy, backup/restore, and security-test evidence before operational use.
