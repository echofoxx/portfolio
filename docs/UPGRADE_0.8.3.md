# Upgrade to v0.8.3

v0.8.3 is a schema-compatible executive UX and travel-assurance release for v0.8.2. Migration head remains `0009_self_service_v080`; there is no new runtime dependency.

## Before upgrading

1. Back up PostgreSQL and the application upload volume.
2. Preserve the deployed `.env`, reverse-proxy configuration, and Compose overrides.
3. Record the currently running version and confirm `/health` is healthy.

## Upgrade

1. Replace the v0.8.2 source/image with v0.8.3.
2. Run `docker compose build --no-cache`.
3. Run `docker compose up -d`.
4. Allow the normal startup migration check; Alembic remains at `0009_self_service_v080`.
5. Do not reseed or replace the database/upload volume during an in-place upgrade.

## Verify

- Confirm the sidebar shows `v0.8.3`.
- Open Display preferences and switch among Light, Dusk, Black, Forest, Navy, Teal, Plum, Steel, and Stone.
- Confirm no “Input area” note appears on project, board, travel, or administration forms.
- Start a project and verify **Blueprint Catalog** remains on one line and aligns beneath the blueprint selector.
- Open Travel & Engagements and verify the four executive map chips, compliance-ring legend, ranked location index, and absence of map-header zoom buttons.
- Hover list items and markers in both directions; click either to open the same location detail.
- Verify wheel/trackpad zoom, drag pan, touch pinch/pan where available, arrow-key pan, plus/minus zoom, `0` refit, and Escape dismissal.
- Apply a region or page filter and confirm the map fits the filtered locations and the empty message never overlays populated markers.
- Run `pytest -q`; the packaged baseline is **115 passed**.

## Rollback

Because v0.8.3 changes no schema, stop the application and redeploy v0.8.2 against the preserved database and upload volume. Restore the backup only if an independent deployment operation changed data.
