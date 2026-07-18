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
