# API Guide

## Local documentation

After sign-in, open `/api/docs`. The generated OpenAPI JSON is available at `/api/openapi.json`. The application disables the default unauthenticated Swagger endpoints and presents an authenticated local API page instead.

## Current API character

Release 0.1.0 is primarily a server-rendered workflow application. Form routes are part of the application contract, while focused JSON operations support interactive behavior such as Kanban movement. External consumers should not treat every form route as a stable public integration API.

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
| POST | `/demands/{uuid}/transition` | stage transition |
| POST | `/demands/{uuid}/assess` | weighted assessment |
| POST | `/demands/{uuid}/decision` | leadership decision |
| POST | `/demands/{uuid}/convert` | approved demand to project |
| GET | `/projects/{uuid}` | execution workspace |
| POST | `/projects/{uuid}/status` | status update and roll-up |
| POST | `/api/tasks/{uuid}/move` | JSON Kanban move |
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
