# Upgrade to v0.4.0

## Supported source release

This guide covers an upgrade from v0.3.1. Upgrade earlier installations through the prior migration guides first.

## 1. Back up

```bash
docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > ddc5i-before-v040.dump
docker run --rm -v ddc5i_storage:/source -v "$PWD":/backup alpine \
  tar -czf /backup/ddc5i-storage-before-v040.tgz -C /source .
```

Confirm both backup files are non-empty before continuing.

## 2. Preserve configuration

Retain the existing `.env`. Add these values:

```env
PUBLIC_BASE_URL=http://localhost:8080
TRUST_PROXY_HOPS=0
RATE_LIMIT_REQUESTS=300
RATE_LIMIT_WINDOW_SECONDS=900
```

For one controlled reverse proxy directly in front of the application, use `TRUST_PROXY_HOPS=1`. Use the exact number of controlled proxy hops. Do not enable unrestricted proxy trust.

## 3. Replace source and rebuild

```bash
docker compose down
# Replace application source with v0.4.0 while retaining .env and named volumes.
docker compose up -d --build
docker compose ps
curl -fsS http://localhost:8080/health/ready
```

Startup runs `alembic upgrade head` and applies `0004_execution_roadmap_v040`.

## 4. Validate

1. Sign in as `admin`.
2. Open Administration and confirm the public URL, trusted proxy hops, rate limit, and file policy.
3. Open a project and verify Board, WBS, Schedule, Status Reporting, and Board Configuration.
4. Open a task through its drawer and full-page fallback.
5. Upload a Markdown or PDF attachment, preview it, upload a replacement version, remove it, and restore it.
6. Create a status-report draft, edit it, submit it, and approve it.
7. Open the War Room and confirm the approved report is visible.
8. Open Blueprints and create a project from a template.

## Migration contents

- Adds project template code/version fields.
- Adds task type, watchers, custom fields, and actual dates.
- Adds attachment version, current state, download, category, and soft-deletion fields.
- Adds board columns, task-note revisions, project templates, and status reports.
- Creates default board columns for existing projects.
- Preserves existing demand, project, task, attachment, audit, and RTM data.

## Rollback

The migration downgrade deliberately does not delete v0.4.0 data-bearing tables. To roll back safely:

```bash
docker compose down
# Restore the v0.3.1 source.
docker compose up -d db
docker compose exec -T db pg_restore --clean --if-exists -U "$POSTGRES_USER" -d "$POSTGRES_DB" < ddc5i-before-v040.dump
# Restore the storage volume from ddc5i-storage-before-v040.tgz.
docker compose up -d --build
```
