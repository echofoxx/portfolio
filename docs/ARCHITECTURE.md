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

`LocalVolumeStorage` validates path, filename, extension, and streamed size, assigns an opaque key, and records SHA-256. The application currently uses workbook upload processing and the adapter boundary; full document lifecycle and records integration are Phase 2 work.

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
