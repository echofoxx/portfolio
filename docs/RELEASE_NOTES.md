# Release Notes

## v0.8.0 — Self-Service Portfolio Operations

### Added

- Added user-created **Division Local** and **Portfolio Managed** projects with governance, funding, and resource posture; blueprint initialization; stable IDs; creator lineage; and audit evidence.
- Added a governed **promotion request** lifecycle. Scope growth, enterprise impact, funding, resource, and schedule needs are reviewed before the same local project becomes portfolio-managed.
- Added eight role-focused dashboard lenses and server-persisted panel order, size, and visibility preferences.
- Added controlled Admin resource-capacity CSV template/export/import with preview, stable-key matching, row-level validation, explicit commit, batch lineage, and audit evidence.
- Added CCD and DDC5I Front Office division profiles and banners; replaced the JFID banner with the corrected source; filled blank profile summaries from supplied banner content.
- Expanded active project blueprints from 3 to 14 and added dedicated project task, milestone, RAID, status-report, resource-request, project, promotion, and import-review forms.
- Added migration `0009_self_service_v080` and seven v0.8.0 acceptance tests.

### Changed

- Made **Divisions** a primary navigation destination and added a global division switcher, dashboard shortcuts, and linked breadcrumbs.
- Reworked Portfolio Overview into an inviting landing page with role language, direct actions, division cards, and smart movable panels.
- Minimized slide-out drawers and embedded create forms; task details have reliable full-page navigation and primary entry workflows use focused pages.
- Restricted division dashboard aggregations to the signed-in user's accessible portfolio scope.
- Moved the high-write SQLite test database to an isolated temporary directory for repeatable attachment and full-suite verification.

### Validation and boundaries

- Full suite: **97 passed**, 0 failed. Python compilation, JavaScript syntax, and clean Alembic upgrade to `0009_self_service_v080` pass.
- Docker Compose target-host validation remains required because Docker is not available in the build environment.
- Resource CSV exchange is Admin-only in v0.8.0 and is a governed seeding/correction interface, not a workforce system integration.

## v0.7.9 — Adoption, Focus & Workflow Simplification

### Added

- Added a unified **My Work Action Center**: a single prioritized queue grouped into Critical now, Awaiting me, Due soon, Needs update, Watching, and Recently completed, with per-item "why", parent, priority, due date, status, and a primary action; empty groups collapse and a single positive empty state replaces empty panels.
- Added governed **quick actions**: inline task percent-complete, task completion, blocker capture, and action close-out from My Work (`POST /quick/tasks/{id}`, `POST /quick/actions/{id}/close`), restricted to the owner or managing PM, CSRF-protected, and audited with before/after evidence.
- Added a **decision-first Portfolio Overview**: Decisions Required and Significant Changes (health deterioration, critical risks, forecast-over-budget, milestone slippage, stale status) render before KPIs; the Investment Flow Sankey moved to a dedicated Investment analysis deep-dive section.
- Added **explainable health rollups**: a "Why? · View calculation" control on Portfolio Health showing formula, status counts, effective-health precedence per project (override → owner → calculated), and data freshness.
- Added **focused Travel workspaces** (Overview, Requests, Trip Reports, Reconciliation, Engagement Outcomes) with server-side pagination at 25 rows per page and filter preservation across views.
- Added a searchable **Help & glossary drawer** (RAID, ROM, RTM, health/calculated/approved status, benefit realization, ROI, authoritative source, reconciliation, determination, stage gate, confidence score) with owner, authoritative source, and workflow location per term.
- Added a role-specific first-login **Getting started** checklist with dismiss/restart, adaptive role-focus strip compaction, and returning-user page-guide collapse.
- Added privacy-conscious local **adoption telemetry hooks** (`window.jsj6Telemetry`): page views, quick-action usage, help usage, glossary/search misses in a local 200-event ring buffer with no network calls and no sensitive data.
- Added `tests/test_v079.py` with nine acceptance tests covering version consistency, navigation structure, the Action Center, quick-action permissions and audit, decision-first ordering, travel view pagination, and accessibility/telemetry markers.

### Changed

- Simplified primary navigation to nine role-visible destinations; Strategy, Scenarios, Decisions, Risks & Dependencies, Roadmaps, Blueprints, Notifications, and saved views moved to a collapsible "More workspaces" group and Administration & Assurance became collapsible — with per-group persistence and automatic expansion when a contained route is active. No authorized capability was removed.
- Replaced the duplicated top workspace tabs with a contextual shortcut strip (Home, My Work with open count, top two role actions, Notifications).
- Travel request and trip report tables no longer render hundreds of rows on initial load; the map and location index are shorter and fit the viewport, with the index scrolling independently.
- Global `prefers-reduced-motion` support and 42px minimum touch targets on mobile; Action Center cards reflow to stacked mobile layout.

### Fixed — release integrity

- Established the `VERSION` file as the single source of truth (`app.config.APP_VERSION`) for FastAPI metadata, the UI footer, static asset cache strings, division-export schema/filename versions, and the CSV package README — resolving drift where the package was labeled 0.7.8 while `VERSION` and tests referenced 0.7.7.
- Root-caused and intentionally updated nine stale test expectations (hard-coded `0.7.7` asset strings, the renamed "Outcome pipeline" label, the inlined world-map asset) rather than suppressing failures.

## v0.7.8 — Dashboard Layout, Realistic Geography & Motion

- Portfolio Overview layout rework (full-width Investment Flow row), locally packaged Natural Earth world map, shorter map panels, horizontal Outcome pipeline, and once-per-element first-load motion honoring `prefers-reduced-motion`. (Backfilled: this section was previously missing from the release notes — part of the v0.7.9 release-integrity sweep.)

## v0.7.7 — Visual Portfolio Intelligence

### Added

- Added an interactive, locally rendered geographic footprint to the Travel dashboard with proportional estimated-cost markers, keyboard selection, linked detail, synchronized Top Locations, mapping coverage, and unmapped-location stewardship cues.
- Added a governed location registry that normalizes known source aliases and typographical variants without modifying original travel records or calling an external geocoding service.
- Added monthly travel cost-and-volume trend, determination mix by division, travel-to-value outcome funnel, report-compliance view, and engagement-impact ranking.
- Added an interactive Portfolio Overview **Investment Flow** Sankey tracing approved budget through financial category, lead division, project, and actual-to-date or unspent-approved outcomes.
- Added reconciled flow totals, source-record drill-through, accessible investment tables, and financial filter support for category, division, and flow outcome.
- Added ten `UX-077`, `TRV-077`, `FIN-077`, and `SEC-077` requirements plus `tests/test_v077.py`.

### Changed

- Relabeled the user-facing **Briefings & Reviews** navigation and page title to **Briefings** while retaining stable `/portfolio-reviews` routes, records, permissions, and audit evidence.
- Changed the dashboard benefit KPI to display the governed benefit unit instead of formatting nonmonetary benefit-index values as currency.
- Updated static asset versioning and packaged release metadata to `0.7.7`.

### Security and accessibility

- Map geometry, location coordinates, Sankey rendering, and chart interactions use locally packaged assets and same-origin JavaScript; no destination or financial data is sent to a map, chart, geocoding, analytics, or CDN service.
- Advanced visuals provide keyboard interaction, descriptive labels, linked-list or table alternatives, server-side drill-through, and usable no-JavaScript source access.
- Travel markers contain city-level aggregate information only and do not present traveler routes or precise traveler positions.

### Boundaries

- Travel costs remain approval estimates, not authoritative actual expenditure.
- The Sankey is labeled **Investment Flow**, not cash flow, because the current baseline is planning and local transaction evidence rather than an authoritative accounting ledger.
- Coordinates are locally stewarded reference points; unresolved locations remain explicitly unmapped.

## v0.7.6 — Travel & Engagement Outcomes

### Added

- Added the Travel & Engagements workspace with filters, approval-estimate KPIs, division/month/status/location summaries, report-compliance indicators, reconciliation workload, and drill-through to requests, engagements, and reports.
- Added canonical `TravelEngagement`, `TravelRequest`, `TravelApprovalStep`, `TripReport`, `TripReportItem`, and `TravelEntityLink` entities and migration `0008_travel_engagements_v076`.
- Added controlled Excel validation, preview, and commit for Travel Requests and Trip Reports, including row-level results, correction guidance, source filename/row, raw payload, source IDs, batch IDs, and audit evidence.
- Added robust XLSX support for Power BI exports that omit explicit A1 cell references.
- Seeded 385 supplied travel requests totaling $1,082,395.25 and nine supplied trip reports.
- Added engagement normalization, report/request candidate scoring, confidence/rationale evidence, conservative auto-match, and human reconciliation.
- Added complete trip-report narratives plus structured finding, recommendation, action, risk, decision, and dependency candidates.
- Added governed report lifecycle status, review comments, reviewer identity, review timestamp, clear/rematch controls, and audit evidence.
- Added promotion of accepted report outcomes into canonical portfolio Actions, RAID risks, Decisions, and Dependencies with clickable source backlinks.
- Added division-page, division-briefing, My Work, global-search, report-center, CSV-export, division-package, data-quality, and audit integration.
- Added twelve `TRV-076` requirements and v0.7.6 acceptance tests.

### Changed

- Division JSON/CSV export schema is now `0.7.6` and includes travel requests and trip reports.
- The standard division briefing now contains sixteen sections, adding **Travel, forums, and external engagement outcomes**.
- Travel cost labels consistently state that values are approval estimates and not authoritative actual expenditures.
- Source external ID `303` is retained despite an invalid date sequence and is treated as a warning/data-quality issue rather than silently corrected or dropped.

### Validation

- The supplied approval dataset reconciles to exactly 385 records and $1,082,395.25.
- All nine supplied trip reports load with full narrative content and structured outcomes.
- Travel dashboard, request/report/engagement drill-through, search, exports, division integration, briefing payload, import preview, and source anomaly handling are covered by `tests/test_v076.py`.
- Python compilation, Jinja template compilation, Alembic migration, and the complete automated test suite are included in build validation.

### Boundaries

- Cost data is approval-estimate data, not authoritative actual travel expenditure.
- Map visualization uses local geographic summaries; production geocoding or map services require an approved integration and security review.
- Narrative sensitivity detection supports review but does not replace authoritative classification/handling determinations.
- Candidate matching requires human confirmation unless a unique match exceeds the conservative auto-match threshold.

## v0.7.5 — Division Experience and Data Exchange

### Added

- Added responsive division-specific banners for JFID, JAD, DSD, CID, C3OD2, and AID using optimized WebP assets, reserved aspect ratios, accessible alternative text, responsive focal points, fade-in loading, graceful fallback, and reduced-motion behavior.
- Rebuilt the Division Portfolios index with visual mission cards, focus tags, live project/demand/exception counts, and direct drill-down.
- Made the Division page the canonical current and briefing experience with a compact view switcher, presentation mode, leadership summary, live KPIs, mission health, delivery portfolio, milestones, RAID, and linked review workspace.
- Added the governed `DivisionProfile` entity for mission, vision, focus areas, responsibilities, branches, initiatives, relationships, forums, doctrine/standards, banner metadata, publishing status, source documents, and review metadata.
- Added approachable profile editing for authorized administrators, PMO, enterprise portfolio owners, data stewards, division chiefs, and division portfolio managers.
- Added division JSON export and multi-file CSV package export for the accessible profile, projects, demands, core functions, capacity, financials, milestones, and RAID records.
- Added JSON and CSV division-profile import with file-size control, normalization, non-destructive preview, explicit commit, validation, permissions, and audit evidence.
- Packaged the supplied division outline and cross-cutting source documents under `docs/source/division-profiles`.
- Added migration `0007_division_experience_v075` and six v0.7.5 RTM requirements.

### Changed

- Corrected CID to **Coalition Interoperability Division** while preserving the stable `CID` code, organization ID, links, projects, demands, reviews, and audit history.
- Corrected JFID to **Joint Fires Integration Division** and C3OD2 to **Cyber & C2 Operational Development Division**.
- Updated the seeded mission narratives and division profiles from the supplied division outlines, doctrine summary, relationship map, and leadership-forum summary.
- Updated static asset versioning to `0.7.5`.

### Validation

- 72 automated tests pass.
- Python compilation passes.
- JavaScript syntax validation passes.
- Jinja route rendering and new profile workflows are covered by automated tests.
- JSON and CSV package contents, profile edit/import audit evidence, banner rendering, corrected division naming, and auditor read-only behavior are covered by `tests/test_v075.py`.

### Boundaries

- v0.7.5 imports only governed division-profile content; bulk project, demand, resource, financial, milestone, and RAID import remains a future controlled-data-exchange work package.
- CID, C3OD2, and AID branch structures remain intentionally blank until confirmed by content owners.
- Formal WCAG 2.2 AA certification, target-host visual regression, and conference-room display acceptance remain required.

## v0.7.0 — Division Briefing & Review

### Added

- Added division-scoped briefing workspaces that use the existing Portfolio Review record as the governance anchor.
- Added a standard 15-section division briefing template covering mission context, accomplishments, portfolio health, demands, milestones, RAID, workforce, investment, benefits, cross-division coordination, decisions required, 30/60/90-day priorities, and prior actions.
- Added source-backed briefing summaries and direct drill-downs to authoritative project, demand, milestone, RAID, dependency, resource, financial, benefit, status-report, and action records.
- Added section owners, narrative preparation, readiness states, submission, division approval, and return-for-change controls.
- Added approved briefing snapshots and post-approval section locking so the application preserves exactly what leadership reviewed even when source records later change.
- Added presentation mode for conference-room briefing without a separate slide deck.
- Added in-review questions, responses, notes, parking-lot items, governed change requests, and direct action assignment.
- Added briefing question and change-request assignments to My Work.
- Added closeout acknowledgement when unresolved questions or change requests remain open.
- Extended audit evidence for briefing preparation, approval, interaction, follow-up, and closure.
- Excluded Restricted, Sensitive, and Limited Distribution project and demand records from the standard briefing payload and enforced auditor-only read access.

### Changed

- Renamed the primary Reviews navigation to **Briefings & Reviews**.
- Updated role focus for division leaders, PMO, and senior leaders to emphasize source-backed briefing preparation and follow-through.
- Updated the product roadmap so v0.8.0 becomes the recommended connected-operations and enterprise-identity release.

### Data model

- Added migration `0006_division_briefing_v070`.
- Added briefing sections, briefing snapshots, review questions, review change requests, and review notes.
- Existing portfolio reviews, decisions, actions, projects, demands, and source records remain authoritative and compatible.

### Validation

- Added automated coverage for briefing creation, default sections, source summaries, lifecycle controls, snapshot capture, questions, responses, change requests, My Work follow-up, and closeout acknowledgement.
- Python and JavaScript static validation pass.
- Jinja templates compile.
- 68 automated tests pass.

## v0.6.1 — Role Guidance and Accessible Workflows

### Added

- Role-based focus profiles with recommended starting actions and Focus markers in navigation.
- Contextual process-flow guides for portfolio, demand, project, review, resource, investment, reporting, scenario, import, data-quality, integration, administration, RTM, audit, and personal-work workflows.
- Display preferences for Standard, Large, and Extra large text plus Comfortable or Compact spacing, persisted in the browser.
- Automatic visual treatment for substantial input forms, required-field markers, and plain-language input instructions.
- Redesigned My Work workbench with summary counts, direct authoritative links, due dates, priority, progress, health, status, and next actions.
- Stronger focus indicators, skip navigation, readable scalable microcopy, and mobile preference behavior.

### Boundaries

- Preferences are browser-local rather than stored in the user profile.
- The release improves accessibility but does not claim WCAG certification.
- Process guides explain current workflows; they do not replace server-side authorization or workflow validation.

### Validation

- 63 automated tests pass.
- Python compilation, JavaScript syntax validation, and Jinja route rendering pass.
- No database migration is required.

## v0.6.0 — Premium Enterprise UX and Dashboard Modernization

### Changed

- Rebranded the application shell and login experience for JSJ6 Enterprise Portfolio Management.
- Introduced a premium high-contrast dark default theme and a complete light alternate theme using shared design tokens.
- Added the requested top navigation and reorganized the left navigation for faster portfolio, quick-access, and administration workflows.
- Rebuilt Portfolio Overview with six KPIs, portfolio health, investment category distribution, recent decisions, assigned work, and a portfolio-at-a-glance table.
- Standardized control heights, action alignment, field sizing, grid behavior, card geometry, table rendering, drawer layout, and responsive breakpoints across the application.
- Removed the legacy War Room route and interface. Its source capabilities remain accessible in Portfolio Overview, Decisions, Risks & Dependencies, Portfolio Reviews, Status Reporting, Scenarios, and Reports & Analytics.

### Validation

- Python and JavaScript static validation pass.
- All Jinja templates compile.
- Automated tests cover the JSJ6 application shell, dashboard content, requested navigation, dark-theme default, light-theme support, and removal of the legacy route.

## v0.5.0 — Portfolio Governance and Enterprise Integration

### Added — platform administration

- Create and update local demonstration users with multiple roles, division scope, active status, and sensitive-record access.
- Register acting-role delegations with delegator, delegate, roles, organization scope, effective dates, rationale, and audit evidence.
- Prevent an active administrator from disabling their own account.
- Expand the Administration workspace with user, organization, delegation, runtime, and security-configuration views.

### Added — portfolio review forum

- Create enterprise or division portfolio reviews with period, chair, participants, agenda, summary, and decisions required.
- Add review items for projects and other governed records with recommendation, rationale, owner, and status.
- Record a review outcome as linked Decision and Action records.
- Complete the review and retain searchable, auditable meeting evidence.

### Added — integration governance and ProjectOS dry run

- Register integration connections and record type, base URL, mode, authentication type, enabled state, health, and configuration metadata.
- Maintain field-ownership rules identifying authoritative system, allowed writers, and conflict policy.
- Generate a canonical ProjectOS project/task/milestone payload and store a dry-run synchronization result without contacting an external endpoint.
- Show recent synchronization attempts, payload evidence, result details, status, attempts, and operator.

### Added — resource and financial workflows

- Submit role- and skill-based resource requests with hours, period, project, organization, priority, rationale, requester, and approver.
- Approve or decline resource requests with resolution and audit evidence.
- Append commitment, obligation, expenditure, forecast-adjustment, and other transaction records to project financial baselines.
- Preserve stable transaction identifiers, source system, reference, date, amount, notes, and creator.

### Added — non-destructive scenario planning

- Create enterprise or division what-if scenarios with baseline date and assumptions.
- Propose supported changes to project, capacity, and financial fields without changing authoritative records.
- Calculate and store baseline-versus-scenario metrics and explanations.
- Separate scenario approval from application.
- Apply only approved changes and record before/after audit evidence for each affected record.

### Added — data-quality and operations command centers

- Run deterministic data-quality scans and persist detected or refreshed issues.
- Assign issue owners and due dates, record dispositions, and resolve issues.
- Generate source-grounded report packs for an organization and reporting period.
- Approve report packs and retain section metrics, narrative, approval metadata, and job-history evidence.
- Persist data-quality and report-generation job runs for operator visibility.

### Search and traceability

- Global search now includes portfolio reviews, scenarios, data-quality issues, report packs, and resource requests while retaining server-side access filtering.
- Updated the 307-row RTM with conservative v0.5.0 design, module, test, acceptance, UAT, and release references.
- Current status: 91 Implemented, 56 Partially implemented, 111 Planned, 27 Requires integration, 12 Requires policy or governance decision, and 10 Deferred.

### Validation

- 57 automated tests passed.
- 83% application-code coverage.
- 44 Jinja templates compiled.
- Clean migration through `0005_portfolio_governance_v050` passed.
- An actual v0.4.0 database upgraded and reseeded without loss of 25 users, 20 demands, 17 projects, 80 tasks, or 307 RTM records.
- Authenticated HTTP smoke checks returned HTTP 200 for Executive, Portfolio Reviews, Scenarios, Integrations, Resources, Financials, Data Quality, Operations, and Administration.
- Docker runtime validation remains required on the target host because a Docker daemon is unavailable in the artifact environment.

### Important boundaries

- The ProjectOS operation is a canonical-contract dry run, not a live external synchronization.
- Microsoft 365 and SharePoint connections are registry entries only until credentials, network access, approved APIs, and field mappings are configured in the target environment.
- Delegation records are governed and auditable, but delegated roles are not yet automatically injected into every authorization decision.
- Job history is persistent, but v0.5.0 does not include an external durable scheduler or distributed worker.
- Resource and financial features remain planning and evidence registers, not authoritative workforce or accounting systems.

## v0.4.0 — Execution and Roadmap Expansion

See the packaged v0.4.0 upgrade guide and repository history for prior release details.
