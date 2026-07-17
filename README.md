# DDC5I Enterprise Portfolio Management MVP

A functional, locally deployable reference implementation for connecting DDC5I strategy and mission to demand intake, assessment, leadership decisions, portfolio delivery, projects, resources, investments, dependencies, outcomes, benefits, audit, reporting, and requirements traceability.

> **Release:** 0.1.0 MVP reference implementation  
> **Deployment:** Docker Desktop / Docker Compose  
> **Web port:** `8080`  
> **Mailpit:** `8025`  
> **Authentication:** local demonstration accounts only; not production SSO, CAC, or PIV  
> **Authorization:** server-side RBAC, organization scope, sensitivity checks, and audit evidence

The application is deliberately honest about coverage. The imported 307-row RTM is classified as **83 Implemented**, **34 Partially implemented**, **131 Planned**, **37 Requires integration**, **12 Requires policy or governance decision**, and **10 Deferred**. The in-app RTM lets administrators update design references, tests, releases, UAT results, acceptance notes, and status.

## What works on the first build

After `docker compose up -d --build`, the application automatically waits for PostgreSQL, runs Alembic migrations, seeds the demonstration environment, starts the web service, and exposes health checks.

A user can immediately:

- Sign in with documented demonstration accounts.
- Open a populated DDC5I executive dashboard and six division dashboards.
- Drill from exceptions into demand, project, milestone, RAID, dependency, owner, financial, and benefit records.
- Create and submit a demand, move it through triage and clarification, score it, route it through stage gates, record a decision, and convert approved work into a project without rekeying.
- Use a project workspace with overview, WBS/task list, Kanban, milestones, RAID, dependencies, actions, financials, benefits, and status update controls.
- See project status changes roll up to division and enterprise views.
- Search, filter, save views, export accessible records, review notifications, and inspect material audit history.
- Upload a versioned demand workbook, preview create/update/duplicate/warning/error/permission outcomes, commit valid rows, and download a correction workbook.
- Inspect all 307 RTM requirements and filter by ID, domain, phase, preliminary fit, implementation status, release, and other traceability fields.

No visible control is intentionally decorative. Capabilities that are not usable are documented as roadmap items instead of being presented as working buttons.

## Screenshots

### Executive portfolio dashboard

![Executive dashboard](docs/screenshots/02-executive-dashboard.png)

### Division dashboard

![Division dashboard](docs/screenshots/03-division-dashboard.png)

### Demand pipeline and governed intake

![Demand pipeline](docs/screenshots/04-demand-pipeline.png)

![Demand detail](docs/screenshots/05-demand-detail.png)

### Built-in project execution

![Project Kanban](docs/screenshots/06-project-kanban.png)

![Project RAID](docs/screenshots/07-project-raid.png)

### Supporting decision data

![Resource capacity](docs/screenshots/08-resource-capacity.png)

![Excel import](docs/screenshots/09-excel-import.png)

![RTM administration](docs/screenshots/10-requirements-rtm.png)

All screenshots are captured from the seeded application in this release. More images are in [`docs/screenshots`](docs/screenshots).

## Architecture

![Architecture](docs/diagrams/architecture.svg)

The MVP is a modular monolith using:

- FastAPI, Jinja, vanilla JavaScript, and locally bundled CSS
- SQLAlchemy and Alembic
- PostgreSQL 16
- Local Docker-volume file-storage adapter
- In-process background-job abstraction with a future durable-queue boundary
- Generated OpenAPI document exposed after authentication
- Mailpit for optional local email capture
- Adapter contracts and a field-ownership registry for future integrations

FastAPI is used instead of the preferred Next.js baseline because it preserves the required local deployment, persistent PostgreSQL data, server-side security, OpenAPI, maintainability, tests, and offline-first behavior while producing a smaller first-build footprint.

See [Architecture](docs/ARCHITECTURE.md), [Canonical Data Model](docs/DATA_MODEL.md), and [Integration Architecture](docs/INTEGRATION_ARCHITECTURE.md).

## System requirements

- Docker Desktop 4.x or Docker Engine with Docker Compose v2
- 4 GB free memory minimum; 8 GB recommended
- 3 GB free disk space for images, database volume, uploads, and backups
- Current enterprise-approved Microsoft Edge or Google Chrome
- Local ports `8080`, `8025`, and `1025` available, or changed in `.env`

No internet connection is required after the container images and Python dependencies have been obtained during the initial build. No external CDN is used at runtime.

## Install on Docker Desktop

### 1. Prepare the folder

Extract this release and open a terminal in the project root—the folder containing `docker-compose.yml`.

### 2. Create local environment settings

macOS or Linux:

```bash
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and replace `POSTGRES_PASSWORD` and `SECRET_KEY`. Generate a local secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 3. Build and start

```bash
docker compose up -d --build
```

### 4. Confirm health

```bash
docker compose ps
curl http://localhost:8080/health/ready
```

Expected response:

```json
{"status":"ready","database":"connected"}
```

### 5. Open the application

- Application: `http://localhost:8080`
- Mailpit: `http://localhost:8025`
- Authenticated API documentation: `http://localhost:8080/api/docs`

The first startup can take several minutes because Docker builds the image, PostgreSQL initializes its volume, migrations run, and 307 requirements plus demonstration records are seeded.

## Demonstration accounts

All demonstration accounts use password `Demo123!`.

| Username | Primary role | Purpose |
|---|---|---|
| `leader` | DDC5I Senior Leader | Enterprise decision dashboard and leadership drill-down |
| `portfolio` | Enterprise Portfolio Owner | Enterprise portfolio oversight |
| `pmo` | PMO / Portfolio Manager | Intake, triage, assessment, portfolio, imports, audit |
| `approver` | Approval Authority | Leadership disposition and conditions |
| `admin` | Platform Administrator | Full local demonstration administration |
| `auditor` | Auditor | Read-only audit and governance review |
| `avery.jad` | JAD Division Chief / Portfolio Manager | Division-scoped access |
| `cameron.dsd` | DSD Division Chief / Portfolio Manager | Division-scoped access |

Additional seeded users represent assessors, project managers, team members, resource managers, financial managers, benefit owners, data stewards, and security reviewers. See Administration as `admin`.

**These credentials are development-only.** Disable local demonstration authentication and connect an approved enterprise identity provider before any operational deployment.

## Major modules

| Module | MVP behavior |
|---|---|
| Executive | Exception-oriented dashboard, decisions, milestones, dependencies, capacity, finance, benefits, stale data, narrative, and metric metadata |
| Divisions | JAD, DSD, AID, CID, JFID, and C3OD2 mission/function/portfolio drill-down |
| Strategy & Mission | Mission and core-function catalog, bidirectional alignment, unaligned-work visibility |
| Demand | Guided intake, draft/submit, organization and sensitivity scope, triage, clarification, assessment, gates, disposition, revision history |
| Assessment | Weighted 100-point model, rationale, confidence, multiple assessors, variance, side-by-side comparison |
| Decisions | Authority, participants, rationale, evidence, conditions, caveats, resource/financial implications, follow-up actions |
| Portfolios & Projects | Six division portfolios, project conversion, execution workspace, WBS/task list, Kanban, milestones, RAID, dependencies, status |
| Resources | Role and skill capacity, allocation, actual effort, over-allocation, minimum core-function coverage |
| Financials | ROM, approved budget, actual, forecast, variance, minimum viable, full requirement, funding status |
| Benefits | Expected/realized values, owner, status, unit, and review date |
| Collaboration | In-app notifications, assignments, workflow updates, comments/rationale fields, local Mailpit option |
| Import / Export | Versioned XLSX templates, demand preview/commit/correction, CSV exports respecting accessible scope |
| Governance | 307-row RTM, audit history, saved views, data-quality indicators, metric definitions, integration registry |

## Demonstration data

The seed tells a coherent cross-division portfolio story and reconciles dashboard totals to source records:

- 7 organizations: DDC5I Enterprise plus six divisions
- 6 division portfolios
- 6 missions and 12 recurring core functions
- 20 demands across lifecycle stages
- 17 projects: 12 active, 3 completed, 2 archived/canceled
- 80 tasks and 35 milestones
- 20 RAID records and 15 dependencies
- 10 decisions and 12 decision/roadblock actions
- 25 users with role and division assignments
- Resource capacity and skill-gap records for all divisions
- Budget, actual, forecast, funding, and benefit records
- Multiple reporting periods, stale records, and deliberate data-quality exceptions
- Cross-division initiatives and a restricted demand
- 307 traceability records

## Key workflow walkthrough

1. Sign in as `admin` or `pmo`.
2. Open **Demand → New Demand**.
3. Complete mission alignment, problem, desired end state, division, sponsor, ROM, and benefit fields.
4. Save as draft or validate and submit.
5. Move through **Triage**, optionally **Clarification Required**, then **Assessment**.
6. Record one or more assessments using the configurable criteria shown in the UI.
7. Move through **Awaiting Portfolio Recommendation** and **Awaiting Decision**.
8. Sign in as `approver`, `leader`, or `admin`; record an authoritative disposition, evidence, conditions, and capacity tradeoff when required.
9. Convert an approved demand to a project. Approved title, mission, division, sponsor, scope, deliverables, target date, cost, benefit, and sensitivity are carried forward.
10. Update project health and progress. Return to Executive or the division dashboard to see the roll-up.

The full script is in [Demonstration Walkthrough](docs/DEMONSTRATION_WALKTHROUGH.md).

## Excel templates

- [`DDC5I_Import_Templates_v1.0.xlsx`](sample-imports/DDC5I_Import_Templates_v1.0.xlsx) — Demands, Projects, Tasks, Risks, Resources, Budgets, Benefits, and Reference Data contracts
- [`DDC5I_Demand_Import_Demo_v1.0.xlsx`](sample-imports/DDC5I_Demand_Import_Demo_v1.0.xlsx) — rows producing success, warning/possible duplicate, duplicate identifier, and validation errors

The MVP commits validated **Demand** rows. The other sheets are versioned contracts for later vertical slices and integrations; they are not falsely presented as working imports.

## Environment variables

| Variable | Default | Purpose |
|---|---:|---|
| `APP_PORT` | `8080` | Host web port |
| `POSTGRES_DB` | `ddc5i_portfolio` | PostgreSQL database |
| `POSTGRES_USER` | `ddc5i` | PostgreSQL user |
| `POSTGRES_PASSWORD` | local placeholder | Replace before startup |
| `SECRET_KEY` | local placeholder | Session and CSRF signing; replace with 32+ random characters |
| `ENVIRONMENT` | `development` | Enables secure-cookie behavior when set to `production` |
| `MAX_UPLOAD_MB` | `10` | Upload size limit |
| `MAILPIT_SMTP_PORT` | `1025` | Local SMTP capture port |
| `MAILPIT_UI_PORT` | `8025` | Mailpit web interface |

## Common operations

### Logs

```bash
docker compose logs -f web db
```

### Stop without deleting data

```bash
docker compose down
```

### Restart

```bash
docker compose up -d
```

### Data reset

This deletes the database and file-storage volumes, then reseeds the application:

```bash
docker compose down -v
docker compose up -d --build
```

### Database migrations

```bash
docker compose exec web alembic current
docker compose exec web alembic upgrade head
```

Create a new revision during development:

```bash
docker compose exec web alembic revision --autogenerate -m "describe change"
```

### Backup

```bash
./scripts/backup.sh
```

### Restore

```bash
./scripts/restore.sh backups/ddc5i-YYYYMMDD-HHMMSS.sql.gz
```

See [Backup and Restore](docs/BACKUP_RESTORE.md) before using these procedures operationally.

## Tests

Run in Docker:

```bash
docker compose run --rm web pytest -q
```

Run with coverage:

```bash
docker compose run --rm web pytest --cov=app --cov-report=term-missing
```

Validated in the release workspace: **25 tests passed with 88% application-code coverage**. Coverage includes scoring, permissions, stage transitions, database uniqueness, import validation, audit before/after evidence, health checks, critical routes, accessible landmarks, division access denial, auditor read-only behavior, project status roll-up, and the full demand-to-project workflow.

The build environment used to create this package did not expose a Docker daemon, so the Compose stack was structurally validated but not launched here. Run the documented Docker health check on the target Docker Desktop host; this limitation is explicitly recorded in the acceptance checklist.

## Security model and production warning

Implemented in the reference MVP:

- PBKDF2-SHA256 password hashing
- Signed, HTTP-only, same-site session cookie
- CSRF verification on state-changing form and API operations
- Server-side role checks
- Division scoping and restricted-record checks
- 404 behavior for inaccessible direct-object references
- Read-only auditor behavior
- Login attempt throttling
- Content security and browser security headers
- Input and import validation
- File extension, name, path, and size controls in the storage adapter
- Material before/after audit events
- Environment-based secrets

Not implemented or authorized:

- RMF authorization or authorization to operate
- CAC/PIV, SAML, OIDC, or enterprise SSO
- DoD records schedule integration
- production-grade centralized logging/SIEM
- malware scanning, data loss prevention, or cross-domain transfer
- approved financial/personnel data connections
- formal Section 508 or WCAG 2.2 AA certification
- production high availability, disaster-recovery exercise, or 99.9% SLA evidence

See [Security and Production Hardening](docs/SECURITY_HARDENING.md).

## Integration strategy

Every future connector must define:

1. Canonical identifiers and schema version.
2. The authoritative owner of each synchronized field.
3. Allowed writers and conflict behavior.
4. Event or API contract, idempotency, retry limits, and dead-letter handling.
5. Source lineage and audit requirements.
6. Reconciliation queries, exception ownership, and operator workflow.
7. Security, privacy, records, and retention controls.

The `app/services/integrations.py` registry prevents ambiguous field ownership by design. ProjectOS, ServiceNow SPM, Microsoft Graph, SharePoint, Advana/WDP, Power BI, Jira, Azure DevOps, financial systems, workforce systems, and enterprise identity remain adapter/integration work rather than hidden MVP dependencies.

## Requirements traceability

- In-app route: **Requirements RTM**
- Machine-readable source: `app/data/requirements.json`
- Exported status report: [`docs/DDC5I_RTM_MVP_Status.csv`](docs/DDC5I_RTM_MVP_Status.csv)
- Narrative report: [Requirements Traceability](docs/REQUIREMENTS_TRACEABILITY.md)

Status is intentionally conservative. An RTM row is marked Implemented only when the reference MVP contains a usable vertical slice and a design/module reference. “Requires integration” and “Requires policy or governance decision” remain explicit.

## Roadmap

The five-phase roadmap is in [ROADMAP.md](docs/ROADMAP.md). Each roadmap work package includes business value, dependencies, related requirement IDs, complexity, primary owner, acceptance criteria, security implications, integration implications, and recommended release.

The recommended next release is **0.2.0 — Portfolio and Execution Expansion**, centered on richer WBS/schedules, reusable blueprints, advanced RAID, recurring report packs, meeting support, document management, and the first governed ProjectOS connector. AI remains after access control, data quality, metrics, lineage, audit, and human review controls are demonstrably mature.

## Documentation index

- [Target Operating Model](docs/TARGET_OPERATING_MODEL.md)
- [Installation Guide](docs/INSTALLATION.md)
- [User Guide by Role](docs/USER_GUIDE.md)
- [Administrator Guide](docs/ADMIN_GUIDE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Canonical Data Model](docs/DATA_MODEL.md)
- [Role and Permission Matrix](docs/ROLE_PERMISSION_MATRIX.md)
- [Integration Architecture](docs/INTEGRATION_ARCHITECTURE.md)
- [API Guide](docs/API.md)
- [Implementation Backlog](docs/IMPLEMENTATION_BACKLOG.md)
- [Assumptions and Open Decisions](docs/ASSUMPTIONS_DECISIONS.md)
- [Requirements Traceability](docs/REQUIREMENTS_TRACEABILITY.md)
- [Demonstration Walkthrough](docs/DEMONSTRATION_WALKTHROUGH.md)
- [Backup and Restore](docs/BACKUP_RESTORE.md)
- [Security and Production Hardening](docs/SECURITY_HARDENING.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Feature Inventory](docs/FEATURE_INVENTORY.md)
- [Known Limitations](docs/KNOWN_LIMITATIONS.md)
- [Roadmap](docs/ROADMAP.md)
- [Test Results](docs/TEST_RESULTS.md)
- [Release Notes](docs/RELEASE_NOTES.md)
- [MVP Acceptance Checklist](docs/MVP_ACCEPTANCE_CHECKLIST.md)

## License and data handling

No license was specified by the requirements artifacts. Add an approved license before external distribution. The seeded data is synthetic demonstration data and must not be interpreted as current operational DDC5I status, funding, personnel, or authoritative decisions.
