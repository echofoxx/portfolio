# v0.8.3.1 Build Validation

## Automated validation

| Check | Result |
|---|---|
| `pytest -q` | **117 passed**, 217 non-failing framework deprecation warnings |
| Focused v0.8.3.1/v0.8.3/v0.8.2 set | **13 passed** |
| Python compilation | Passed for travel service and application modules |
| `node --check app/static/app.js` | Passed |
| Route/template rendering | Passed through authenticated regression tests |
| Alembic compatibility | Existing head `0009_self_service_v080`; no migration |
| Application version | `0.8.3.1` from `VERSION` |

## v0.8.3.1 functional evidence

- The Linked Map Index reads the rendered canvas height and remains synchronized through responsive resizing.
- The index header and stewardship summary remain fixed while the Top Locations list scrolls internally.
- Input Area banner source and styling are absent.
- Nine themes render with browser-persistence hooks and legacy dark-to-Dusk migration.
- Location compliance reconciles completed required travel to linked and overdue reports.
- Direct pointer, wheel, touch/pinch, double-click, and keyboard hooks replace map-header zoom buttons.
- Hidden empty/detail states cannot be overridden by component display CSS.
- Map/list linkage, anchored detail, executive chips, compliance legend, and unmapped exposure render from the authenticated Travel route.

---

# Prior v0.8.2 Build Validation

## Automated validation

| Check | Result |
|---|---|
| `pytest -q` | **111 passed**, 209 non-failing framework deprecation warnings |
| Python compilation | Passed for application and migration Python modules |
| `node --check app/static/app.js` | Passed |
| Jinja template compilation and route rendering | Passed |
| Alembic compatibility | Existing head `0009_self_service_v080`; v0.8.2 adds no migration |
| Application version | `0.8.2` (single source: `VERSION` → `app.config.APP_VERSION`) |
| Clean seed | 8 divisions, 14 active project blueprints, 27 demo users |

## v0.8.2 functional evidence

- Full RAID IDs remain visible on one line; narrative cells retain responsive wrapping.
- Board Governance groups its editable workflow states under one guidance banner; Travel guidance spans the complete filter row.
- Portfolio KPI and eight-division grids use equal-height, content-fit desktop and responsive layouts.
- Focused task breadcrumbs link to valid HTML routes; the task collection path redirects to the board.
- Role-focus and sidebar controls retain accessible names and visible compact/mobile states.
- Travel map region/measure controls, zoom/fit, clusters, URL state, linked locations, summary metrics, and privacy wording render from the filtered local payload.

## Prior v0.8.1 functional evidence

- Project overview renders structured narrative, accountability, schedule comparison, variance, progress, and three isolated project signal cards.
- Gantt labels render WBS, title, and date range as separate semantic elements.
- RAID and dependency tables render responsive metadata/narrative classes and mobile record-card labels.
- Briefings register links to `/portfolio-reviews/new`; the register contains no embedded creation form; create and cancel navigation is verified.
- Enterprise Roadmap filter and action groups render separately from Current Forecast.
- Portfolio Overview contains the three-value Investment Summary and no Sankey payload; `/financials/flow` contains the full visualization and source records.
- Compact, Standard, and Wide dashboard size tokens are applied consistently through the persisted preference workflow.

## v0.8.0 functional evidence

- JFID corrected banner, CCD banner, and FO banner render from optimized same-origin WebP assets with populated profile summaries.
- Division navigation is available from the primary menu, topbar switcher, dashboard, and breadcrumbs.
- Local and portfolio-managed projects initialize governed boards/tasks/milestones from selected blueprints.
- Promotion approval updates the same local project record to portfolio-managed and retains its ID.
- Dashboard panel preferences persist order, size, and hidden state per user; role defaults remain recoverable.
- Admin resource CSV import performs preview, validation, create/update/unchanged classification, explicit commit, and audit evidence.
- Division dashboard aggregation reuses permission-scoped project and demand collections.
- Dedicated task, milestone, RAID, status-report, project, promotion, resource-request, and import-review pages render and retain server-side permission and CSRF enforcement.

## v0.7.7 functional evidence

- Portfolio Overview renders the Investment Flow payload, conserved summary, local SVG Sankey, accessible category table, and financial/project drill-through.
- Financial flow filters support category, division, actual-to-date, and unspent-approved views.
- Travel renders the local world outline, normalized location payload, proportional markers, linked Top Locations, and city-level detail.
- Location aliases such as source typographical variants normalize to governed canonical destinations while original source values remain unchanged.
- Seeded mapping coverage exceeds 95%; unmapped values are explicitly listed for stewardship.
- Monthly trend, determination by division, outcome funnel, report compliance, reconciliation, and engagement impact share the same accessible filtered population.
- Briefings is relabeled without changing stable routes or data records.
- Static assets are cache-versioned `0.7.7` and remain compatible with the self-only Content Security Policy.

## Regression evidence

All prior demand, project, task, schedule, governance, scenario, resource, financial, data-quality, integration, division, briefing, import, travel, search, audit, and permission tests pass.

## Manual target-host validation required

- Docker Compose build/start and PostgreSQL upgrade against an operational v0.7.6 backup.
- Browser visual regression at desktop, laptop, tablet, mobile, and conference-room resolutions.
- Keyboard, screen-reader, reduced-motion, 200% zoom/reflow, and formal WCAG 2.2 AA review.
- Representative scale/performance testing for significantly larger project and destination populations.
- Security, privacy, classification/handling, records-retention, coordinate stewardship, and source-owner approval.
- Signed UAT by financial managers, travelers, division portfolio managers, division chiefs, data stewards, PMO, leaders, auditors, and security reviewers.
