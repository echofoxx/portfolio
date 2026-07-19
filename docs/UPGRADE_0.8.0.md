# Upgrade to v0.8.0 — Self-Service Portfolio Operations

## Scope

v0.8.0 is a schema-changing upgrade from v0.7.9. It adds self-service project classification and promotion, server-persisted dashboard preferences, CCD and Front Office division identities, resource-capacity exchange, focused form pages, direct division navigation, and an expanded blueprint catalog.

Migration head changes from `0008_travel_engagements_v076` to `0009_self_service_v080`.

## Before upgrading

1. Confirm the source installation is healthy and at migration head `0008_travel_engagements_v076`.
2. Back up PostgreSQL and the attachment-storage volume together; test the restore in a separate environment.
3. Preserve `.env`, reverse-proxy configuration, external secrets, and persistent volumes.
4. Export a current organization and project inventory for post-upgrade reconciliation.
5. Schedule a maintenance window; do not allow project or resource updates during the database migration.

## Upgrade procedure

1. Stop application writers: `docker compose down` or stop the application service.
2. Replace the application source with the v0.8.0 package while preserving environment and persistent volumes.
3. Rebuild and start: `docker compose up --build -d`. Container startup applies Alembic migrations automatically.
4. Confirm `/health/live` and `/health/ready` return healthy responses.
5. Confirm the database revision is `0009_self_service_v080`.
6. Run the idempotent seed once if it is not part of startup: `python -m app.seed`. This adds reference blueprints and fills only blank division-profile fields; it does not overwrite populated user content.
7. Hard-refresh browsers once so static assets load with `?v=0.8.0`.

For a non-container installation:

```bash
python -m alembic upgrade head
python -m app.seed
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Database changes

`0009_self_service_v080` adds these nullable/defaulted project fields:

- `governance_level`
- `funding_posture`
- `resource_posture`
- `promotion_status`
- `created_by_id`

It also adds:

- `project_promotion_requests` for request, decision, rationale, conditions, requester/reviewer, and timestamps;
- `dashboard_preferences` for per-user role lens, panel order, hidden panels, and panel sizes; and
- a safe organization-code reconciliation from legacy `FRONT` to `FO`, preserving the existing organization ID and links.

Existing projects remain portfolio-managed by default. No existing task, milestone, RAID, attachment, demand, financial, briefing, travel, or audit record is deleted.

## Post-upgrade validation

- Open **Divisions** directly and verify JFID, CCD, and FO banners and mission summaries.
- Create a Division Local project from a blueprint and verify no portfolio is required.
- Submit and approve a promotion request; verify the project ID and existing tasks do not change.
- Personalize Portfolio Overview, reload, and verify panel order/size/visibility persists.
- As Admin, export the resource template, preview a one-row import, commit it, and export resources again.
- Verify a division-scoped user sees only authorized division dashboard counts and switcher entries.
- Run `pytest -q`; the packaged result is 97 passing tests.

## Rollback and recovery

Prefer restoring the coordinated pre-upgrade database and attachment-volume backup, then redeploying v0.7.9. Do not run a schema downgrade after users have created v0.8.0 projects, promotion requests, or dashboard preferences unless those records have been exported and their loss has been explicitly approved. A forward fix is normally safer after production writes begin.

## User communication

- Divisions is now directly accessible from the main navigation and topbar switcher.
- New Project distinguishes division-local work from portfolio-managed work.
- Promotion changes governance on the existing project; it does not create a replacement project.
- Primary create workflows now open focused pages; users can follow linked breadcrumbs back to the parent record.
- Portfolio Overview starts with a role-focused layout and can be personalized.
- Resource import/export is restricted to Administrators in this release.
