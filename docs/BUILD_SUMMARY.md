# JSJ6 Enterprise Portfolio Management v0.8.0 Build Summary

v0.8.0 is the **Self-Service Portfolio Operations** release. It turns the prior decision and reporting baseline into a more navigable working environment where divisions can initiate local work, promote it when scope changes, use role-focused configurable dashboards, exchange resource seed/correction data under Admin control, and move through focused form pages with linked breadcrumbs.

- Migration head: `0009_self_service_v080`.
- Division identity: corrected JFID plus new CCD and DDC5I Front Office profiles/banners.
- Project governance: Division Local and Portfolio Managed classifications with stable-ID promotion.
- Navigation: direct Divisions primary item, switcher, dashboard links, and breadcrumbs.
- Forms: dedicated pages for primary project and resource entry workflows; embedded create forms are visually retired.
- Dashboards: eight role lenses with server-persisted smart panel order, visibility, and size.
- Resource data: Admin CSV template/export/preview/commit workflow with audit evidence.
- Blueprints: 14 active, versioned project/task structures.
- Validation: **97 automated tests passed**, Python compilation passed, JavaScript syntax passed, and clean Alembic upgrade passed.
- Known environment boundary: Docker target-host validation remains required because Docker is unavailable in the build environment.

---

# Prior v0.7.9 Build Summary

v0.7.9 is the **Adoption, Focus & Workflow Simplification** release on top of the v0.7.8 visual baseline: simplified nine-destination navigation, a unified My Work Action Center with governed quick actions, decision-first executive dashboards with explainable health rollups, focused Travel workspaces with server-side pagination, adaptive guidance and role-specific onboarding, a searchable help/glossary drawer, privacy-conscious adoption telemetry hooks, and a release-integrity sweep making `VERSION` the single source of truth.

- Migration head remains `0008_travel_engagements_v076`; v0.7.9 requires no database schema migration.
- No new Python or JavaScript dependencies.
- Test suite: 89 passing (80 regression + 9 new acceptance tests).
- Division export schema and package metadata are versioned `0.7.9` from the `VERSION` file.

## Prior summary (v0.7.7)


## Delivered

v0.7.7 adds **Visual Portfolio Intelligence** to the v0.7.6 travel-and-engagement lifecycle.

The build includes:

- a locally rendered interactive travel map with proportional estimated-cost markers, aggregate location detail, synchronized Top Locations, and stable location-filter drill-through;
- a governed destination registry that combines known aliases and typographical variants while retaining original source location evidence;
- visible mapping coverage and an unmapped-location stewardship queue;
- travel cost-and-volume trend, determination mix by division, outcome funnel, report-compliance view, reconciliation queue, and engagement-impact ranking;
- a Portfolio Overview **Investment Flow** Sankey tracing approved budget through category, lead division, project, actual-to-date, and unspent-approved outcomes;
- conserved flow totals, reconciliation status, financial/project drill-through, financial flow filters, and an accessible category table;
- simplified **Briefings** navigation while preserving `/portfolio-reviews`, briefing governance, snapshots, permissions, and audit history;
- benefit-unit-aware KPI presentation so nonmonetary benefit-index data is not presented as currency;
- local map geometry and same-origin JavaScript with no external map, geocoding, chart, analytics, or CDN dependency;
- ten new v0.7.7 requirements, increasing the packaged RTM from 325 to 335 rows; and
- four v0.7.7 acceptance tests plus updated regression expectations.

## Data and schema

- Migration head remains `0008_travel_engagements_v076`; v0.7.7 requires no database schema migration.
- Clean seed remains 385 travel requests totaling $1,082,395.25 in approval estimates and 9 trip reports.
- The local registry maps more than 95% of seeded travel requests; unresolved values remain visible rather than guessed.
- Division export schema and package metadata are versioned `0.7.7`.

## Validation completed

- **81 automated tests passed**.
- Python compilation passed for application and migration modules.
- JavaScript syntax validation passed.
- Jinja templates compiled and principal dashboard, travel, briefing, financial, and drill-through routes rendered.
- The packaged RTM contains 335 rows and the release CSV was regenerated from the governed JSON source.

## Transparent boundaries

- Travel values are approval estimates, not authoritative actual expenditures.
- Map points are approximate city-level reference coordinates, not traveler routes or precise traveler positions.
- Investment Flow is planning and local transaction evidence, not an authoritative accounting or cash-flow statement.
- Formal target-host browser, accessibility, performance, security, records, and signed role UAT remain required before operational acceptance.
