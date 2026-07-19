# Architecture

![Modular monolith architecture](diagrams/architecture.svg)

## Architecture decision

The MVP is a modular monolith. Business modules share one deployable application and one PostgreSQL database, while service contracts isolate storage, background work, authentication, and enterprise integrations. This keeps the first build supportable and transactional while preserving boundaries that can later become services.

## Repository structure

```text
app/
  main.py                 routes, authorization orchestration, UI/API handlers
  models.py               canonical SQLAlchemy relational model
  seed.py                 idempotent demonstration seed
  config.py               environment configuration
  database.py             engine and session boundary
  services/
    security.py           authentication, password, RBAC, scope, CSRF
    scoring.py            weighted assessment and variance
    workflow.py           lifecycle transition rules
    audit.py              material before/after audit events
    imports.py            demand import validation and row outcomes
    xlsx_reader.py        local XLSX parsing
    integrations.py       adapter protocols and field-ownership registry
    jobs.py               background-job abstraction
    storage.py            secure local-volume adapter
    briefings.py           source-backed division briefing aggregation and section generation
  templates/              server-rendered pages
  static/                 local CSS, JavaScript, templates
  data/requirements.json  imported RTM baseline
migrations/               Alembic migration environment and revisions
tests/                    unit, integration, access, workflow, import, audit tests
e2e/                      primary acceptance workflow tests
docs/                     guides, diagrams, screenshots, traceability, roadmap
scripts/                  entrypoint, backup, restore
sample-imports/           versioned Excel workbooks
```

## Request flow

1. Browser sends a request with a signed session cookie.
2. `current_user` resolves the user from PostgreSQL.
3. route-level authorization checks role, division, project/record scope, and sensitivity.
4. state-changing operations validate CSRF and business rules.
5. SQLAlchemy writes canonical records inside one database transaction.
6. material operations add an audit event in the same transaction.
7. response renders the authoritative record or redirects with feedback.

## Security boundaries

- Authentication is local demonstration auth only.
- Authorization is server-side and never relies on hidden UI controls.
- Inaccessible records return 404 to reduce direct-object disclosure.
- Restricted records require an explicit flag or security/admin role.
- Auditor role is read-only.
- Sensitive financial rate notes are not shown on general dashboards.
- imports enforce organization and sensitivity scope.

## Persistence and migration

PostgreSQL is the primary datastore. Alembic owns schema evolution. Docker named volumes preserve database and local files across container restarts. The seed is idempotent and does not overwrite populated environments.

## Background work

`InlineJobRunner` provides a simple execution contract for notifications, reports, import processing, reconciliation, and scheduled checks. It records status, timestamps, result, and failure. Production should replace it with a durable queue/worker while preserving the interface.

## Storage

`LocalVolumeStorage` validates path, filename, extension, streamed size, and selected binary signatures, assigns an opaque key, and records SHA-256. Task attachments maintain logical file identity, version/current state, safe preview eligibility, download count, soft-deletion/restoration metadata, and audit evidence. Malware scanning, DLP/CDR, legal hold, retention/disposition, and enterprise repository integration remain production work.

## API

FastAPI generates OpenAPI from route definitions. The authenticated local documentation page links to `/api/openapi.json`. The existing routes are primarily server-rendered workflows plus focused JSON endpoints such as Kanban movement. A stable, versioned external REST surface is a Phase 2/3 hardening item.

## Scalability path

Possible extraction order without redesigning core identifiers:

1. notification and scheduled job worker;
2. import/export service;
3. integration/reconciliation worker;
4. reporting read model;
5. document storage adapter;
6. scenario and optimization engine.

Business events and canonical IDs should be introduced before extraction. Database ownership must remain explicit.

## Performance and availability

The local MVP is designed for demonstration-sized datasets. PostgreSQL indexes key IDs, statuses, and audit timestamps. Production performance work requires representative load, pagination, query plans, caching/read models, asynchronous reports, and a measured 95th-percentile interaction target. High availability and a 99.9% objective are design goals, not demonstrated claims.


## v0.3.0 execution-workspace flow

1. The project page renders canonical task cards and WBS rows.
2. CSP-compatible JavaScript requests the authorized task-panel fragment.
3. Every task-panel route revalidates project/task access server-side; the client-provided identifier is not trusted.
4. Form mutations enforce CSRF, role/project scope, validation, audit, and notification rules.
5. Attachment bytes pass through the storage adapter while metadata and evidence hashes remain in PostgreSQL.
6. Search queries each authorized canonical record family and returns ranked, direct links; the suggestion endpoint applies the same scope.

This remains a modular-monolith boundary. Task collaboration, storage, search, and schedule logic can later move behind services without changing stable task/project identifiers.


## v0.3.1 progressive task navigation and demand revision flow

### Task navigation

1. Kanban and WBS task actions render as standard links to `/projects/{project}/tasks/{task}`.
2. The local v0.3.1 JavaScript bundle progressively enhances those links by opening the in-project drawer and fetching the `/panel` fragment.
3. If the bundle is stale, blocked, or disabled, normal link navigation opens the same authorized task workspace as a full page.
4. Both routes resolve the task through the same server-side project, division, sensitivity, and role checks.
5. Static asset URLs carry the application version to prevent an older Docker-deployed bundle from being reused after upgrade.

### Submitted-demand revision

1. The detail page calculates edit eligibility from identity, role, organization, sensitivity, and lifecycle stage.
2. The edit form carries the displayed demand version.
3. On save, the server rejects a stale version, revalidates access and submission readiness, applies field changes, increments the version, and writes a `DemandRevision` plus material `AuditEvent` in the same transaction.
4. Accountable users receive in-app notifications that link to the authoritative demand.
5. Direct edits are locked after Assessment begins so scoring, recommendations, and leadership decisions continue to reference a stable evaluated baseline.


## v0.4.0 execution and reporting flow

1. Each project owns ordered `BoardColumn` records. Task creates, edits, and JSON moves validate project scope, target-column state, and WIP before commit.
2. `schedule.py` derives WBS numbering, detects finish-to-start cycles, calculates a transparent basic critical path, and prepares Gantt layout data without mutating source tasks.
3. A `ProjectTemplate` version is immutable input to a governed instantiation transaction that creates the project, board, WBS, milestones, notes, and dependencies while recording template code/version on the project.
4. `StatusReport` records move through Draft/Returned → Submitted → Approved. Approved versions become immutable governed reporting baselines; return/resubmit creates accountable review flow.
5. Task files use a logical-file/version model. Replacements create a new current version; prior versions stay retrievable under authorization. Removal is soft deletion and restoration is audited.
6. Client identity is resolved from the socket peer when direct or from exactly `TRUST_PROXY_HOPS` controlled right-most forwarding hops. Rate-limit keys never trust arbitrary left-most client input.

## v0.5.0 governance and integration-control flow

1. Authorized users create portfolio-review, resource-request, scenario, quality, report-pack, and integration-control records through server-rendered forms protected by CSRF and server-side role/scope checks.
2. SQLAlchemy persists stable UUIDs, human-readable identifiers, status, ownership/scope, timestamps, source evidence, and audit records in PostgreSQL.
3. The ProjectOS adapter builds a canonical payload from accessible Project, Task, and Milestone records. Mock/dry-run mode stores the request/result in `sync_runs` and intentionally performs no external network write.
4. Field ownership is persisted independently of connection configuration so future adapters can reject conflicting writes and route discrepancies to reconciliation.
5. Scenarios store proposed changes and calculated results separately from authoritative records. Only an approved scenario can invoke the apply path, which records before/after audit evidence per target.
6. Data-quality scans and report generation create persistent `job_runs`, but execute in-process in v0.5.0. A durable queue/worker remains an explicit adapter boundary.
7. Search includes the new governance records using the same user/division/sensitivity filters as the rest of the application.

This preserves the modular-monolith approach: governance modules share one transaction boundary and canonical model now, while integration, scheduling, reporting, identity, and storage boundaries can later move behind independently scalable services without replacing stable identifiers or core workflows.


## v0.7.0 division briefing and live-review flow

1. A `PortfolioReview` with type `Division Briefing` remains the governing review header and enforces enterprise or division scope.
2. `briefings.py` creates the standard 15 `BriefingSection` records and refreshes source summaries from authorized project, demand, milestone, RAID, dependency, workforce, financial, benefit, status-report, and action records.
3. Section narratives and readiness states are prepared without changing the authoritative source records summarized by the section.
4. Submission requires every section to be ready. Division approval creates a `BriefingSnapshot` containing the frozen source-backed payload and section narrative presented to leadership.
5. Presentation mode reads the approved snapshot while direct source links remain available for authorized drill-down. Later changes to a source record do not rewrite the approved snapshot.
6. `ReviewQuestion`, `ReviewChangeRequest`, and `ReviewNote` capture discussion and follow-up. Existing `Decision` and `Action` records remain the authoritative outcome registers.
7. Assigned questions and change requests appear in My Work. Closing a briefing with unresolved items requires explicit acknowledgement and retains the open follow-up.
8. Migration `0006_division_briefing_v070` adds only the new briefing support tables and does not rewrite existing review, decision, action, project, or demand records.


## v0.7.5 division experience and data-exchange flow

1. The Division Portfolios index resolves each accessible division by stable organization code and joins its governed `DivisionProfile`.
2. `_division_hero.html` renders a local optimized WebP asset with fixed aspect-ratio space, profile-controlled focal point, alternative text, loading state, fallback treatment, and reduced-motion support.
3. The division detail route builds one access-filtered workspace from authoritative project, demand, core-function, capacity, financial, milestone, and RAID records. Current and briefing modes are presentation variants of that same data, not duplicated stores.
4. Profile edits require approved roles, division scope, CSRF validation, normalized business-language fields, and material audit evidence. Auditors remain read-only.
5. JSON export emits a versioned structured package. CSV export emits a ZIP of related flat files. Both apply the same division and sensitivity filters used by the page.
6. Profile import accepts only size-limited JSON or CSV, normalizes and validates content, renders a non-destructive preview, and requires a separate explicit commit before updating the governed profile.
7. Migration `0007_division_experience_v075` creates `division_profiles` and corrects display names without changing organization codes, IDs, or linked operational records. Idempotent seeding adds missing profile/banner metadata without overwriting maintained content.

## v0.7.6 Travel & Engagement Outcomes architecture

The travel capability follows the existing layered application pattern:

1. **Source ingestion:** `app/services/xlsx_reader.py` reads standard XLSX files and Power BI exports with positional cells.
2. **Validation and normalization:** `app/services/travel.py` validates controlled columns, normalizes divisions/dates/costs/titles/locations, records warnings, and generates source-aware stable keys.
3. **Canonical persistence:** migration `0008_travel_engagements_v076` and the six travel models retain approvals, reports, outcomes, links, and provenance.
4. **Reconciliation:** candidate scoring uses traveler, division, date overlap/proximity, normalized event title, and destination. Only unique high-confidence candidates may auto-link; all other cases remain visible for human confirmation.
5. **Outcome governance:** report items are reviewable records. Promotion creates or links canonical portfolio entities and adds `TravelEntityLink` backlinks.
6. **Presentation:** the Travel workspace, request/report/engagement detail pages, Division Portfolio, Division Briefing, My Work, search, reports, and data quality all read the same canonical entities.
7. **Evidence:** every import, match, review, promotion, export, and correction is protected by role/org/sensitivity checks and audit records.

No live mapping or external geocoding dependency is required for the packaged local build. Destination summaries degrade gracefully and avoid sending source destinations to an unapproved network service.

## v0.7.7 local visualization architecture

v0.7.7 keeps advanced visualization inside the existing trusted application boundary:

- server-side services aggregate only records already authorized for the current user;
- `resolve_location` maps known source aliases to locally maintained canonical city-level coordinates while preserving source strings;
- the Travel template embeds escaped aggregate JSON and references a local world-outline SVG;
- the Portfolio Overview embeds an approved-budget flow payload whose links conserve source financial totals;
- `app/static/app.js` progressively renders markers and SVG flow nodes with keyboard labels and linked source-record actions;
- linked lists and tables remain available without JavaScript; and
- the self-only Content Security Policy remains unchanged, with no external map, geocoding, chart, analytics, font, or CDN dependency.
