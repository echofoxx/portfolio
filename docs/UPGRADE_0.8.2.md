# Upgrade to v0.8.2

v0.8.2 is a schema-compatible presentation and navigation hotfix for v0.8.1. Migration head remains `0009_self_service_v080`; no new database migration or runtime dependency is introduced.

## Before upgrading

1. Back up the PostgreSQL database and application upload volume.
2. Preserve the deployed `.env` and review local reverse-proxy or compose overrides.
3. Confirm the current application is healthy and record the running version.

## Upgrade

1. Replace the v0.8.1 application source/image with v0.8.2.
2. Rebuild and restart the application using the existing deployment procedure.
3. Allow normal startup migration checking; Alembic should remain at `0009_self_service_v080`.
4. Do not reseed or replace the database/upload volume during an in-place upgrade.

## Verify

- Confirm the sidebar shows `v0.8.2` and Sign out is available when the sidebar is expanded and compact.
- Open Project RAID and verify a full identifier such as `RAID-26-011` is visible on one line.
- Open Board Settings and verify one full-width Input area banner appears above Board Governance.
- Create a task, follow every breadcrumb link, and confirm no 405 response occurs.
- Open Portfolio Overview and verify six compact KPI cards and eight evenly arranged division cards.
- Open Travel & Engagements and verify the guidance banner, region and measure selectors, zoom, fit, clusters, linked locations, and privacy wording.
- Run `pytest -q`; the packaged baseline is 111 passing tests.

## Rollback

Because v0.8.2 changes no schema, stop the application and redeploy the v0.8.1 application image/source against the preserved database and upload volume. Restore the backup only if an independent deployment operation changed data.
