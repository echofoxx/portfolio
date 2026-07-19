# Upgrade to v0.7.7 — Visual Portfolio Intelligence

## Scope

v0.7.7 is a schema-compatible application upgrade from v0.7.6. It adds local interactive visualizations, travel-location normalization, financial-flow drill-through, and simplified Briefings labels. No new Alembic migration is required; migration head remains `0008_travel_engagements_v076`.

## Upgrade steps

1. Back up the database and persistent storage.
2. Replace the v0.7.6 application files with the v0.7.7 package while retaining environment configuration and uploaded storage.
3. Run `alembic upgrade head` to confirm the database remains at the packaged migration head.
4. Restart the application and force-refresh browsers so `/static/app.css?v=0.7.7` and `/static/app.js?v=0.7.7` are loaded.
5. Run `pytest -q` and confirm 81 tests pass in the packaged environment.
6. Open **Portfolio Overview** and verify the Investment Flow renders, reconciles, and opens financial/project records.
7. Open **Travel** and verify the local world map, linked Top Locations, trend, determination mix, outcome funnel, compliance, and engagement-impact sections render.
8. Verify the side and top navigation show **Briefings** while existing `/portfolio-reviews` links continue to work.

## Data and security notes

- No travel record or financial record is migrated or rewritten.
- Original location strings remain authoritative source evidence; the new registry only provides an analytical canonical destination and approximate city-level coordinate.
- Map and Sankey rendering use same-origin assets and JavaScript. No data is sent to external map, geocoding, chart, analytics, or CDN services.
- Travel costs remain approval estimates.
- Investment Flow is planning and local transaction evidence, not an authoritative accounting or cash-flow statement.

## Rollback

Because v0.7.7 introduces no schema migration, rollback consists of restoring the v0.7.6 application image/files and restarting the service. Restore the database backup only if unrelated operational changes occurred after the upgrade.
