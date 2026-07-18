# Upgrade to v0.6.0

v0.6.0 is a presentation and navigation release. It does not add a database migration and is compatible with the existing v0.5.0 PostgreSQL volume.

## Upgrade

1. Back up the database and storage volume using the packaged backup procedure.
2. Extract v0.6.0 into a clean directory and retain the existing `.env` values.
3. Compare `.env.example`; optionally set `APP_NAME=JSJ6 Enterprise Portfolio Management`.
4. Rebuild and restart: `docker compose up -d --build`.
5. Open the application in a new browser tab. Static assets are versioned as `0.6.0`, preventing an older cached interface from being reused.

## Verification

- Confirm the JSJ6 brand, top navigation, reorganized sidebar, and Portfolio Overview dashboard appear.
- Confirm Premium Enterprise Dark is the first-run theme and the theme control switches to the complete light interface.
- Open Demand Intake, Projects, Resources, Investments, Reports & Analytics, Scenarios, and Administration to verify aligned fields, buttons, cards, and tables.
- Confirm `/war-room` returns 404. Use Portfolio Overview, Decisions, Risks & Dependencies, Portfolio Reviews, Status Reporting, and reporting views for the retained leadership workflows.
- Run `pytest -q` and confirm the packaged automated suite passes.

## Rollback

Because there is no v0.6.0 database migration, application rollback consists of stopping v0.6.0 and restarting the prior v0.5.0 application against the same backed-up volumes. Restore the backup only if business data changed after the upgrade and a point-in-time rollback is required.
