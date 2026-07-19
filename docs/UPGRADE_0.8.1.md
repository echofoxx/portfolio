# Upgrade to v0.8.1 — Responsive Portfolio Presentation Hotfix

## Scope

v0.8.1 is a schema-compatible update from v0.8.0. It changes templates, CSS, JavaScript dashboard sizing, routes, tests, and documentation. It does not add or alter database tables, columns, seed identities, attachments, or integration contracts.

## Before upgrading

1. Confirm the current deployment is v0.8.0 and healthy.
2. Back up the PostgreSQL volume and attachment/storage volume using the normal operational procedure.
3. Preserve the current `.env`, secrets, reverse-proxy configuration, and persistent-volume mappings.

## Docker Compose upgrade

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
docker compose ps
curl -fsS http://localhost:${APP_PORT:-8080}/health/ready
```

Startup still runs Alembic through head `0009_self_service_v080`; no new migration is expected. Existing dashboard preferences remain valid. The Investment panel continues to use the stable preference key `investment` and now renders as the smaller summary panel.

## Browser refresh

Static assets are cache-versioned with `0.8.1`. A normal reload should fetch them; use a hard refresh if a browser retains prior Gantt, RAID, roadmap, or dashboard styling.

## Acceptance checks

1. Open a project Overview and confirm its three detail panels and three navigation metrics are aligned.
2. Open Timeline / Gantt and confirm WBS, title, and dates are visually separate.
3. Open RAID & Dependencies at desktop and narrow widths; confirm page-level horizontal scrolling is absent.
4. Open Briefings, select New briefing or review, and verify Create and Cancel.
5. Open Enterprise Roadmap and confirm Apply/Reset are separated from Current Forecast.
6. Open Portfolio Overview and confirm Investment Summary contains Approved, Actual to Date, and Unspent Approved only.
7. Select Investment Summary and verify the full `/financials/flow` visualization, filters, reconciliation, and source tables.
8. Customize dashboard panels and verify Compact, Standard, and Wide behavior.

## Rollback

Because v0.8.1 has no schema migration, application source may be rolled back to v0.8.0 while retaining the database. Restore the coordinated backup if any unrelated operational data problem occurs during deployment.
