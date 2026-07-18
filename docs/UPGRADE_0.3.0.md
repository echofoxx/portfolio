# Upgrade to v0.3.0

v0.3.0 is an in-place upgrade from v0.2.0. It adds task-workspace columns and three new relational tables. Existing PostgreSQL data and named Docker volumes remain authoritative.

## Before upgrading

1. Stop business changes during the maintenance window.
2. Back up PostgreSQL and the file-storage volume.
3. Record the current release and migration revision:

```bash
docker compose exec web alembic current
```

4. Preserve `.env`; do not overwrite local secrets or port changes.

## Upgrade

Replace the application source with v0.3.0 while retaining `.env` and Docker volumes, then run:

```bash
docker compose up -d --build
docker compose exec web alembic current
docker compose ps
curl -fsS http://localhost:8080/health/ready
```

Expected migration head:

```text
0002_task_workspace_v030
```

Startup automatically runs `alembic upgrade head`. The migration adds:

- `tasks.description`
- `tasks.priority`
- `tasks.tags`
- `task_comments`
- `task_attachments`
- `task_relationships`

## Validate after upgrade

1. Sign in as `admin`.
2. Open a project and select **Kanban** or **WBS**.
3. Open a task detail drawer.
4. Save task notes, add a checklist item, and post a comment.
5. Upload a small permitted test file and download it.
6. Search for the task identifier and confirm it appears first.
7. Confirm the search box has no visible `K` artifact.
8. Review the task activity/audit view.
9. Run:

```bash
docker compose run --rm web pytest -q
```

## Rollback

Application rollback is safest through restore rather than destructive downgrade:

1. Stop the v0.3.0 stack.
2. Restore the pre-upgrade PostgreSQL backup and file-storage backup.
3. restore the v0.2.0 source tree and `.env`.
4. Start the stack and verify health.

Alembic downgrade is not the preferred production rollback because it removes v0.3.0 task comments, attachments metadata, relationships, and added task fields. If used in a disposable environment:

```bash
docker compose exec web alembic downgrade 0001_initial
```

Back up uploaded files separately; deleting attachment metadata does not automatically constitute an approved records disposition.
