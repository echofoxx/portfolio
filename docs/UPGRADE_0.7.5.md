# Upgrade Guide — v0.7.5

## Purpose

v0.7.5 introduces the Division Experience release: division-specific visual banners, a governed division profile, corrected authoritative division names, a canonical current/briefing division view, and JSON/CSV profile and portfolio exchange.

## Before upgrading

1. Back up the PostgreSQL database and the application storage volume.
2. Preserve the current `.env` and any reverse-proxy configuration.
3. Confirm the deployment has enough storage for approximately 1 MB of optimized division banner assets.
4. Review any local template or CSS modifications because `division_detail.html`, `divisions.html`, `app.css`, and `app.js` changed substantially.

## Upgrade procedure

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

The container entrypoint runs:

```bash
alembic upgrade head
python -m app.seed
```

Migration `0007_division_experience_v075` creates `division_profiles` and corrects the display names for CID, JFID, and C3OD2. Stable organization codes, IDs, linked projects, demands, portfolios, briefings, actions, and audit history are preserved.

## Post-upgrade checks

1. Sign in as an administrator.
2. Open **Briefings → Division Portfolios**.
3. Confirm all six division cards show a banner.
4. Open CID and confirm the title is **Coalition Interoperability Division**.
5. Switch between **Current view** and **Briefing view**.
6. Use **Present** and exit full-screen.
7. Export CID as JSON and CSV.
8. Open **Edit profile**, confirm the seeded mission details, and cancel without saving.
9. Open **Import profile JSON/CSV**, upload a previously exported profile, review the preview, and cancel unless an update is intended.
10. Confirm the Audit workspace records profile edits/imports and division exports.

## Rollback

Restore the pre-upgrade database and deployment artifact. The Alembic downgrade removes the `division_profiles` table; it does not attempt to restore the previous incorrect display names.

## Important boundaries

- Full portfolio JSON/CSV export is included; v0.7.5 import intentionally updates only the governed division profile.
- Branch structures for CID, C3OD2, and AID remain conservative where no dedicated authoritative branch outline was supplied.
- The banner artwork is optimized into WebP for delivery. Source image masters are not required at runtime.
- Target-host accessibility, conference-room display, browser compatibility, and performance acceptance remain deployment responsibilities.
