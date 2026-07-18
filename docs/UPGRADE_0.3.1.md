# Upgrade to v0.3.1

v0.3.1 is a compatibility hotfix for v0.3.0. It does not add or remove business-data columns. It adds task-navigation reliability, a full task-workspace route, governed editing for submitted demand records, browser-cache versioning, tests, documentation, and an evidence-only RTM migration.

## Before upgrading

1. Back up PostgreSQL and the task-attachment storage volume.
2. Retain the existing `.env` file and named Docker volumes.
3. Record the currently deployed version and confirm the stack is healthy.

```bash
docker compose ps
./scripts/backup.sh
```

## Upgrade

Stop the existing application, replace the source tree with v0.3.1 while retaining `.env` and Docker volumes, and rebuild:

```bash
docker compose down
docker compose up -d --build
docker compose ps
```

Startup runs `alembic upgrade head`. Migration `0003_v031_reliability_hotfix` updates the RTM evidence for DMD-008 and PRJ-007; it does not alter demand, task, attachment, or project data.

## Validate

1. Sign in and confirm the sidebar footer reports `v0.3.1`.
2. Open a project Board and select **Open details** on a task. Confirm the right-side workspace opens.
3. Open the same task in a new tab using its link and confirm the full task page works.
4. Open a Submitted demand owned by the current requester and confirm **Edit Demand** is available.
5. Save a change summary and confirm the demand version and revision history increase.
6. Confirm an Assessment-stage demand does not expose direct editing to the requester.

The generated page references `/static/app.js?v=0.3.1` and `/static/app.css?v=0.3.1`, so a normal reload should retrieve the new assets. A hard refresh is no longer the primary recovery mechanism.

## Rollback

Because the migration changes only RTM evidence, application rollback is primarily a source/container rollback. Restore the previous v0.3.0 source and rebuild. Business data created through v0.3.1 remains compatible with v0.3.0 schema, but submitted-demand revisions created by v0.3.1 remain valid historical records.
