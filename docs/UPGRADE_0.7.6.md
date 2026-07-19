# Upgrade to v0.7.6 — Travel & Engagement Outcomes

## Purpose

v0.7.6 adds a traceable lifecycle from approval-source travel data through post-trip outcomes and portfolio follow-through:

`Travel request → approval evidence → engagement → trip report → reviewed outcome → action/risk/decision → division briefing`

Approval costs remain explicitly labeled as estimates and are not represented as authoritative actual expenditures.

## Before upgrading

1. Back up the application database and persistent upload volume.
2. Record the current migration revision with `alembic current`.
3. Confirm that the v0.7.5 application is healthy and that all pending imports or briefing approvals are complete.
4. Review role assignments for `DATA_STEWARD`, `DIVISION_PORTFOLIO_MANAGER`, `DIVISION_CHIEF`, `PMO`, `AUDITOR`, and `SECURITY_REVIEWER`.

## Upgrade

```bash
docker compose down
docker compose build --no-cache
docker compose run --rm web alembic upgrade head
docker compose up -d
```

For a local Python deployment:

```bash
python -m pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

The idempotent seed reconciliation loads the supplied demonstration travel artifacts only when the travel tables are empty. It does not overwrite existing travel records on subsequent starts.

## Database migration

Migration `0008_travel_engagements_v076` creates:

- `travel_engagements`
- `travel_requests`
- `travel_approval_steps`
- `trip_reports`
- `trip_report_items`
- `travel_entity_links`

The migration adds indexes for stable IDs, external source IDs, organization scope, dates, engagement links, request/report links, matching status, review status, and promoted entity links.

## Source data and expected validation

The packaged source files are retained under `docs/source/travel/`:

- `Trip data.xlsx`
- `Trip Report.xlsx`
- `Travel Dashboard.pdf`

A clean seed must produce:

| Measure | Expected |
|---|---:|
| Travel requests | 385 |
| Approval estimated cost | $1,082,395.25 |
| Trip reports | 9 |
| Source date-sequence warnings | 1 |

The source row with external ID `303` has a return date before its departure date. v0.7.6 retains both values, imports the row with a warning, and surfaces the anomaly through data quality. It does not silently rewrite source evidence.

## Post-upgrade verification

1. Sign in as `admin` with the demonstration password.
2. Open **Travel & Engagements** and confirm the approval estimate total and 385 request records.
3. Open travel request source ID `426` and verify purpose/ROI, impact, J6 funding, exemption category, and two approval steps.
4. Open **Trip Reports** and confirm nine reports with full narrative sections.
5. Confirm that ambiguous reports display candidate matches and require reconciliation.
6. Open a Division Portfolio and confirm the Travel, Forums, and Trip Reports section.
7. Open a Division Briefing and confirm the Travel, Forums, and External Engagement Outcomes section.
8. Export Travel Requests CSV and Trip Reports CSV.
9. Run the data-quality scan and verify travel date, missing-report, and unmatched-report rules.
10. Run `pytest -q`.

## Rollback

Stop the v0.7.6 application, restore the pre-upgrade database backup, and redeploy the v0.7.5 image. Alembic downgrade is implemented for development use, but database restoration is the preferred production rollback because v0.7.6 may contain new source evidence and review decisions.

## Security and operational boundaries

- This reference implementation does not provide production CAC/PIV/SSO.
- Sensitivity detection from narrative text is a safeguard, not an authoritative classification determination.
- Mapping is represented as destination summaries in the local build; an approved mapping service may be integrated later.
- Approval cost estimates must not be used as authoritative financial actuals.
