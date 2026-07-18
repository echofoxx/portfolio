# API Guide

## Local documentation

After sign-in, open `/api/docs`. The generated OpenAPI JSON is available at `/api/openapi.json`. The application disables the default unauthenticated Swagger endpoints and presents an authenticated local API page instead.

## Current API character

Release 0.5.0 is primarily a server-rendered workflow application. Form routes are part of the application contract, while focused JSON operations support interactive behavior such as Kanban movement. External consumers should not treat every form route as a stable public integration API.

## Health endpoints

- `GET /health/live` — process liveness; no authentication required.
- `GET /health/ready` — PostgreSQL readiness; no authentication required.

## Authentication

Local authentication uses `POST /login` and an HTTP-only signed cookie. State-changing authenticated requests require the CSRF token rendered in page metadata/forms. This is not an external OAuth API.

## Representative routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/dashboard` | executive roll-up |
| GET/POST | `/demands/new` | guided intake and submit/draft |
| GET | `/demands/{uuid}` | authoritative demand detail |
| GET/POST | `/demands/{uuid}/edit` | governed pre-assessment revision of eligible demand records |
| POST | `/demands/{uuid}/transition` | stage transition |
| POST | `/demands/{uuid}/assess` | weighted assessment |
| POST | `/demands/{uuid}/decision` | leadership decision |
| POST | `/demands/{uuid}/convert` | approved demand to project |
| GET | `/projects/{uuid}` | execution workspace |
| POST | `/projects/{uuid}/status` | status update and roll-up |
| POST | `/api/tasks/{uuid}/move` | JSON Kanban move |
| GET | `/projects/{project_id}/tasks/{task_id}` | full authoritative task workspace and no-JavaScript fallback |
| GET | `/projects/{project_id}/tasks/{task_id}/panel` | render authorized task workspace drawer fragment |
| POST | `/projects/{project_id}/tasks/{task_id}/update` | update task plan, owner, contributors, dates, effort, notes, and evidence |
| POST | `/projects/{project_id}/tasks/{task_id}/comments` | add persistent comment and mention notifications |
| POST | `/projects/{project_id}/tasks/{task_id}/checklist` | add checklist item |
| POST | `/projects/{project_id}/tasks/{task_id}/attachments` | upload permitted task file |
| GET | `/projects/{project_id}/tasks/{task_id}/attachments/{attachment_id}` | authorized file download |
| POST | `/projects/{project_id}/tasks/{task_id}/relationships` | add task relationship |
| POST | `/projects/{project_id}/tasks/{task_id}/wbs-action` | sequence, indent, outdent, or baseline WBS item |
| GET | `/search` | access-aware comprehensive search |
| GET | `/api/search/suggest` | type-ahead result suggestions |
| POST | `/imports` | XLSX preview |
| POST | `/imports/{uuid}/commit` | commit valid import rows |
| GET | `/exports/demands.csv` | scoped demand export |
| GET | `/exports/projects.csv` | scoped project export |
| GET | `/requirements` | RTM administration |

## External API roadmap

A production external API should add:

- `/api/v1` versioning;
- OAuth2/OIDC service authentication and scopes;
- pagination and consistent error envelopes;
- ETag/optimistic concurrency;
- idempotency keys for creates/events;
- stable schemas and deprecation policy;
- rate limiting and gateway controls;
- classification and data-marking headers;
- correlation IDs and structured audit;
- service-level field-ownership enforcement;
- webhook/business-event signing;
- reconciliation endpoints.

The integration registry already supplies the conceptual boundary for these controls.


## v0.3.1 file and task-route controls

Task-file routes enforce authenticated project access, CSRF on mutations, configured size limits, extension allow-list, safe storage keys, lightweight binary signatures for selected formats, and SHA-256 evidence metadata. These routes are application form/file contracts, not a stable external document API. Operational integration requires approved malware scanning, records management, encryption, and service authentication.

## v0.3.1 demand revision controls

The submitted-demand edit route enforces record access, lifecycle-stage eligibility, CSRF, a form-version match, server-side submission readiness, sensitivity scope, required change summary, audit evidence, revision history, and accountable-user notifications. It is an application workflow route rather than a stable external integration API.


## v0.4.0 execution, reporting, and document routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/roadmaps` | scoped portfolio/project roadmap |
| GET | `/templates` | project-blueprint catalog |
| POST | `/templates/{template_id}/instantiate` | create a project from an immutable blueprint version |
| POST | `/projects/{project_id}/board-columns` | create a governed project column |
| POST | `/projects/{project_id}/board-columns/{column_id}/update` | update name, WIP, and criteria |
| POST | `/projects/{project_id}/board-columns/{column_id}/move` | reorder a column |
| POST | `/projects/{project_id}/board-columns/{column_id}/archive` | archive an unused column |
| POST | `/projects/{project_id}/status-reports` | create or submit a report |
| GET | `/projects/{project_id}/status-reports/{report_id}` | authoritative report detail/print view |
| POST | `/projects/{project_id}/status-reports/{report_id}/update` | update Draft/Returned report and optionally resubmit |
| POST | `/projects/{project_id}/status-reports/{report_id}/approve` | approve and lock reporting baseline |
| POST | `/projects/{project_id}/status-reports/{report_id}/return` | return submitted report for correction |
| GET | `/projects/{project_id}/tasks/{task_id}/attachments/{attachment_id}/preview` | authorized safe preview for supported formats |
| POST | `/projects/{project_id}/tasks/{task_id}/attachments/{attachment_id}/restore` | authorized restore of a soft-deleted version |

These are authenticated application routes. A production external API still requires `/api/v1`, service authentication, stable schemas, pagination, idempotency, and a deprecation policy.

## v0.5.0 governance routes

The following authenticated application routes extend the operational contract. They are server-rendered/form endpoints unless otherwise documented:

- `GET/POST /integrations`
- `POST /integrations/{connection_id}/health`
- `POST /integrations/{connection_id}/sync`
- `POST /integrations/rules`
- `GET/POST /portfolio-reviews`
- `GET /portfolio-reviews/{review_id}`
- `POST /portfolio-reviews/{review_id}/items`
- `POST /portfolio-reviews/{review_id}/items/{item_id}/decide`
- `POST /portfolio-reviews/{review_id}/complete`
- `POST /resources/requests` and decision route
- `POST /financials/transactions`
- `GET/POST /scenarios` plus change/calculate/approve/apply routes
- `GET /data-quality`, scan, and issue-update routes
- `GET /operations`, report-pack generation, and approval routes
- administration user create/update and delegation create routes

These routes require session authentication, CSRF on mutations, role checks, and organization/project scope checks. They are not a stable public integration API. External adapters should use versioned canonical REST/event contracts introduced in a later release.
