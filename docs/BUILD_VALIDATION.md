# v0.8.0 Build Validation

## Automated validation

| Check | Result |
|---|---|
| `pytest -q` | **97 passed**, 175 non-failing framework deprecation warnings |
| Python compilation | Passed for application and migration Python modules |
| `node --check app/static/app.js` | Passed |
| Jinja template compilation and route rendering | Passed |
| Alembic compatibility | Clean upgrade passed through `0009_self_service_v080`; new tables and project fields asserted |
| Application version | `0.8.0` (single source: `VERSION` → `app.config.APP_VERSION`) |
| Clean seed | 8 divisions, 14 active project blueprints, 27 demo users |

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
