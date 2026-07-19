# Test Results — v0.8.3.1

## v0.8.3.1 release result

- Full suite: **117 passed, 0 failed** in 26.55 seconds, with 217 non-failing Starlette deprecation warnings.
- Focused v0.8.3.1/v0.8.3/v0.8.2 compatibility set: **13 passed**.
- New patch coverage verifies rendered-canvas height synchronization and internally scrolling ranked locations.
- Python compilation and JavaScript syntax passed.
- Existing head remains `0009_self_service_v080`; no migration.
- Docker/graphical browser validation remains required on the target host because neither is available in the build environment.

---

# Historical Test Results — v0.8.3

- Full suite: **115 passed, 0 failed**, with 215 non-failing Starlette deprecation warnings.
- Coverage verifies nine themes, clean forms, Blueprint Catalog alignment, per-location linked/overdue compliance, direct map interactions, list↔marker linkage, empty-state integrity, and executive map chips.

---

# Historical Test Results — v0.8.2

## v0.8.2 release result

- Full suite: **111 passed, 0 failed**, with 209 non-failing Starlette deprecation warnings.
- v0.8.2 acceptance tests: **7 passed**, covering release identity, full RAID IDs, grouped input guidance, compact/even dashboard grids, task breadcrumbs, icon/sidebar controls, and regional map lenses.
- Python module and migration compilation: passed.
- JavaScript syntax (`node --check app/static/app.js`): passed.
- Jinja template compilation and authenticated principal-route rendering: passed.
- Alembic compatibility: existing head `0009_self_service_v080`; no v0.8.2 migration.
- Docker Compose validation: not run because Docker is unavailable in the build environment; target-host verification remains required.

---

# Historical Test Results — v0.8.1

## v0.8.1 release result

- Full suite: **104 passed, 0 failed**, with 191 non-failing Starlette deprecation warnings.
- v0.8.1 acceptance tests: **7 passed** covering project overview, Gantt label separation, responsive RAID tables, governance create/cancel page, roadmap actions, dedicated Investment Flow, and uniform dashboard sizes.
- Two historical Investment Flow assertions were intentionally updated because the full chart moved from Portfolio Overview to `/financials/flow` by requirement.
- Python module and migration compilation: passed.
- JavaScript syntax (`node --check app/static/app.js`): passed.
- Jinja template compilation and principal route rendering: passed.
- Clean Alembic upgrade: passed through existing head `0009_self_service_v080`; no v0.8.1 schema migration.
- Docker Compose validation: not run because Docker is unavailable in the build environment; target-host verification remains required.

---

# Historical Test Results — v0.8.0

## v0.8.0 release result

- Full suite: **97 passed, 0 failed**.
- v0.8.0 acceptance tests: **7 passed** covering direct divisions and banners, local project creation, stable-ID promotion, Admin resource preview/commit/export, persisted dashboard preferences, 14-blueprint catalog, and focused project-entry pages.
- Python module and migration compilation: passed.
- JavaScript syntax (`node --check app/static/app.js`): passed.
- Clean Alembic upgrade: passed from base through `0009_self_service_v080`.
- Schema assertions: promotion and dashboard-preference tables present; all five project governance fields present.
- Clean seed assertions: 8 divisions, 14 active blueprints, 27 demonstration users.
- Docker Compose validation: not run because Docker is unavailable in the build environment; target-host verification remains required.

Framework emitted 175 Starlette template-signature deprecation warnings. They are non-failing technical debt and do not change release behavior.

---

# Historical Test Results — v0.7.7

## Summary

- Automated tests: **89 passed** (80 regression + 9 new v0.7.9 acceptance tests).
- Framework deprecation warnings: 134; no test failures.
- Python compilation: passed.
- JavaScript syntax validation: passed.
- Jinja template compilation and principal route rendering: passed.
- RTM regeneration: 335 rows.

## v0.7.7 acceptance evidence

| Area | Evidence |
|---|---|
| Location normalization | Known aliases and source typographical variants resolve to canonical destinations; mapping coverage exceeds 95% |
| Interactive travel map | Local map asset, JSON-backed markers, aggregate detail, Top Locations synchronization, and location filter render |
| Travel analytics | Monthly trend, determination mix, outcome funnel, report compliance, reconciliation, and engagement impact render |
| Investment Flow | Approved budget flows through category, division, project, actual-to-date, and unspent-approved outcomes |
| Reconciliation | Investment Flow summary conserves approved values within rounding tolerance |
| Drill-through | Sankey nodes open financial filters or projects; travel locations open filtered request/report populations |
| Accessibility | Keyboard labels and selection, table/list alternatives, and source links are present |
| Security | Visualizations use local assets and same-origin JavaScript under the existing CSP |
| Briefings label | User-facing labels show Briefings while `/portfolio-reviews` remains functional |
| Regression | All prior v0.1.0–v0.7.6 automated tests pass |

## Primary v0.7.7 test module

`tests/test_v077.py` covers location normalization and coverage, map and travel analytics rendering, Investment Flow rendering and basis, Briefings relabeling, static versioning, and financial drill-through filters.


## v0.7.9 validation summary

- Full suite: `pytest` → **89 passed, 0 failed** (Python 3.12, SQLite test database).
- New acceptance tests (`tests/test_v079.py`): version single-source consistency; simplified navigation with collapsible groups; adaptive shell, glossary, and onboarding markers; Action Center groups with empty-group collapse; quick task update permission + audit evidence; quick update rejected for non-owner (403); decision-first dashboard ordering with explainable health; Travel focused views with 25-row pagination and safe view fallback; reduced-motion and telemetry markers.
- Root-caused stale expectations (not suppressed): hard-coded `0.7.7` asset strings in seven suites now assert against `app.config.APP_VERSION`; `test_v077` updated for the intentional "Outcome pipeline" rename and the inline packaged world map; `test_v060`/`test_v070`/`test_v076` updated for the intentional v0.7.9 navigation and Action Center redesign.
- Authorization: quick actions verified server-side for owner/managing-PM/ADMIN/PMO; CSRF enforced; audit events (`QUICK_UPDATE`, `QUICK_CLOSE`) asserted with before/after values.
- Responsive review: 1440 / 1024 / 768 / 390 px rules reviewed in CSS; Action Center reflows to stacked cards, decision row collapses to one column, help drawer is full-screen, touch targets ≥42px, and `prefers-reduced-motion` disables animation globally. (No headless browser is packaged; visual confirmation performed against the running dev server.)
