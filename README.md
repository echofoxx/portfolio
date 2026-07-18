# JSJ6 Enterprise Portfolio Management MVP

A functional, locally deployable reference implementation for connecting JSJ6 strategy and mission to demand intake, assessment, leadership decisions, portfolio delivery, projects, resources, investments, dependencies, outcomes, benefits, audit, reporting, and requirements traceability.

> **Release:** 0.6.0 — Premium Enterprise UX and Dashboard Modernization  
> **Deployment:** Docker Desktop / Docker Compose  
> **Web port:** `8080`  
> **Mailpit:** `8025`  
> **Authentication:** local demonstration accounts only; not production SSO, CAC, or PIV  
> **Authorization:** server-side RBAC, organization scope, sensitivity checks, and audit evidence

The application is deliberately honest about coverage. The imported 307-row RTM is classified as **91 Implemented**, **56 Partially implemented**, **111 Planned**, **27 Requires integration**, **12 Requires policy or governance decision**, and **10 Deferred**. v0.6.0 modernizes the complete interface without changing those coverage claims. The in-app RTM lets administrators update design references, tests, releases, UAT results, acceptance notes, and status.

## What is new in v0.6.0

- Rebranded the application shell as **JSJ6 Enterprise Portfolio Management**.
- Rebuilt the dashboard around six portfolio KPIs, portfolio-health and investment-category visualizations, recent decisions, assigned work, and a drill-down portfolio table.
- Made the premium high-contrast dark interface the default and retained a purpose-built light theme using the same component geometry and hierarchy.
- Added the requested top navigation and reorganized the left navigation into Portfolio, Quick Access, and Administration sections.
- Standardized buttons, form fields, filter bars, action groups, cards, tables, drawers, and responsive breakpoints to correct alignment and clipping across the application.
- Removed the legacy War Room route, template, navigation entry, and current-user workflow. Leadership decisions, approved status reports, risks, scenarios, and portfolio reviews remain available through their authoritative workspaces.

## What is new in v0.5.0

### User, role, scope, and delegation administration

- Administrators can create, update, activate, and deactivate local users; assign multiple roles, division scope, and sensitive-record access; and prevent self-deactivation of the active administrator account.
- Acting-role delegations retain delegator, delegate, role set, organization scope, effective period, rationale, status, creator, and audit evidence. The v0.5.0 registry is operational; automatic use of delegated roles in every authorization decision remains a documented hardening item.
- Administration presents the current organization, user, role, delegation, runtime, and configuration state in one workspace.

### Portfolio review and decision forum

- Portfolio owners and division leadership can create review periods, select scope, assign chair and participants, build agenda/recommendation items, capture rationale, and complete the forum.
- Deciding a review item creates linked authoritative Decision and Action records so meeting outcomes return to the operational registers rather than remaining isolated notes.
- Review access honors enterprise versus division scope and links from governance items back to portfolio evidence.

### Integration registry, ownership, and ProjectOS dry-run

- Administrators and data stewards can register ProjectOS, Microsoft 365, SharePoint, or other adapter endpoints, record mode/authentication metadata, run configuration health checks, and inspect synchronization history.
- Field ownership rules declare the authoritative system, allowed writers, and conflict policy for each synchronized entity field.
- The ProjectOS adapter generates a canonical project/task/milestone payload and records a complete dry-run result without performing a remote write. Live authentication, network connectivity, retries, and reconciliation remain integration-dependent.

### Resource requests and financial transaction evidence

- Resource managers and authorized portfolio staff can submit role/skill/hour requests against a project and organization, record period, priority, rationale, approval/decline, approver, resolution, and audit history.
- Financial managers can append commitment, obligation, expenditure, forecast-adjustment, and related transaction evidence to project financial records with source, reference, date, notes, and stable identifiers.
- Existing capacity, allocation, budget, forecast, actual, variance, underfunding, and benefit views remain available for decision support.

### Non-destructive scenario planning

- Authorized users can define portfolio what-if scenarios, add proposed changes against allowed project, resource-capacity, and financial fields, calculate baseline-versus-scenario metrics, approve the scenario, and apply it through a separate governed action.
- Draft and calculated scenarios never modify live records. Application requires approval before apply and records before/after audit evidence for every applied change.
- v0.5.0 provides deterministic comparison for the supported fields; dependency propagation, schedule simulation, and optimization remain roadmap capabilities.

### Data-quality and operations command centers

- Data stewards can run deterministic quality scans, assign issue owners and due dates, record dispositions, resolve issues, and drill back to supported source records.
- Current rules identify stale/missing status, alignment, ownership, schedule, dependency, and related portfolio-control conditions from authoritative records.
- Operations can generate source-grounded report packs, review section metrics and narrative, approve packs, and inspect job history. Jobs are persisted as operational evidence; an external durable scheduler/worker is not yet included.

### v0.5.0 validation

- **57 automated tests passed** with **83% application-code coverage**.
- All **44 Jinja templates** compiled, authenticated HTTP smoke checks passed for the new workspaces, and Python/JavaScript static validation completed.
- A clean migration and an in-place v0.4.0-to-v0.5.0 migration preserved 25 users, 20 demands, 17 projects, 80 tasks, and all 307 RTM rows.
- Seed data adds one portfolio review, one resource request, one financial transaction, one scenario, three integration connections, field-ownership rules, one report pack, and job-history evidence.
- Docker Compose could not be launched in the artifact environment because the Docker daemon is unavailable; target-host container validation remains required and documented.

## What is new in v0.4.0

### Execution management and schedule assurance

- Configurable project Kanban columns with persistent ordering, entry/exit criteria, archive controls, and server-enforced WIP limits.
- Hierarchical WBS numbering, parent tasks, task types, baseline dates, actual dates, custom fields, contributors, watchers, and audited sequence/indent actions.
- Dependency validation rejects circular finish-to-start chains. A transparent basic critical-path calculation and baseline-aware Gantt view support schedule review.
- Project roadmaps plot accessible work across the portfolio horizon with health and record drill-down.

### Task documents and evidence

- Version-controlled task attachments preserve logical file identity, version number, current/superseded state, SHA-256 evidence, download count, category, sensitivity, and uploader.
- PDF, PNG, JPEG, Markdown, text, CSV, and JSON support safe in-browser preview. Office documents remain secure downloads.
- File removal is soft deletion with authorized restoration; history remains visible and auditable.
- Working-note revisions retain author, timestamp, complete note snapshot, and change summary.

### Reusable delivery blueprints

- Seeded General Project, Joint Assessment Event, and Data/Standards Initiative blueprints create a complete project, board, WBS, milestones, initial notes, dependencies, and traceability.
- Projects retain the immutable template code and version used to initialize them. Existing projects are never silently changed by later blueprint versions.

### Governed status reporting and executive roll-up

- Status reports support draft, update, submit, return, resubmit, approve, period/version identity, audit, and notifications.
- Approved reports become the source-grounded reporting baseline available from project status and enterprise reporting views. Decisions requested in approved reports appear in the leadership decision queue.
- Project status report pages support browser print/PDF and link back to requirement and audit evidence.

### Deployment hardening

- Exact trusted-proxy hop configuration resolves the client address without unrestricted proxy trust. This addresses reverse-proxy/rate-limit identity issues for Synology, Nginx, Traefik, and controlled tunnel deployments.
- Configurable rate limits protect login, write, and API paths and return standard limit/retry headers.
- Administration displays the non-secret effective proxy, rate-limit, public URL, and file-policy configuration.

### v0.4.0 validation

- **50 automated tests passed** with **83% application-code coverage**.
- All **37 Jinja templates**, Python modules, and JavaScript syntax validated.
- Clean migration and an in-place v0.3.1-to-v0.4.0 migration preserved 17 projects, 80 tasks, and 20 demands.
- Clean seed includes 85 board columns, three versioned project blueprints, eight approved demonstration status reports, and all 307 RTM records.
- Docker Compose could not be launched in the artifact environment because the Docker CLI/daemon is unavailable; target-host validation remains required and documented.

## What is new in v0.3.1

### Task detail reliability

- Kanban and WBS task controls are now real links to a shareable full task page, not button-only JavaScript actions.
- When JavaScript is available, the same links open the right-side task drawer and load the detailed workspace.
- When JavaScript is stale, blocked, or unavailable, the browser follows the link to the full task workspace instead of doing nothing.
- Static CSS and JavaScript URLs include the application version so Docker upgrades do not silently reuse an older browser bundle.
- Drawer failures now provide a direct **Open Full Task Page** recovery action.

### Governed submitted-demand editing

- A requester or sponsor can edit a **Submitted** demand before assessment begins.
- Requesters can also correct **Clarification Required** records and resubmit them.
- PMO, Division Portfolio Manager, Enterprise Portfolio Owner, and Administrator roles can edit eligible Triage records.
- Every save uses an optimistic version check, requires a change summary, increments the demand version, creates a revision record and audit event, and notifies accountable users.
- Assessment, recommendation, decision, approved, and execution-stage demands remain locked against direct editing to preserve the evaluated and approved baseline.

### Validation

- 41 automated tests pass, including task drawer/full-page fallback, versioned static assets, requester editing of submitted demand records, revision/audit evidence, and late-stage edit locking.
- No database schema change is required; migration `0003_v031_reliability_hotfix` updates RTM evidence for existing installations.

## What is new in v0.3.0

### Project task workspace

- Project task cards and WBS rows open a right-side **Task Workspace** without losing project context.
- Task detail now persists description and acceptance criteria, priority, owner, contributors, dates, baseline due date, estimated and actual effort, percent complete, tags, working notes, and acceptance evidence.
- Checklists can be created, completed, reopened, and removed.
- Task-to-task relationships support finish-to-start, start-to-start, finish-to-finish, and related links.
- Comments support `@username` mentions and generate in-app notifications.
- Task changes, comments, files, checklist activity, assignments, and WBS actions are audit recorded.

### Secure task files and evidence

- Authorized users can upload and download PDF, DOCX, XLSX, PPTX, CSV, TXT, Markdown, JSON, PNG, JPG, and JPEG files.
- File handling enforces configured size limits, safe filenames, allowed extensions, lightweight binary-signature checks, SHA-256 evidence hashes, project access rules, and controlled deletion.
- Task attachments remain on the Docker storage volume and retain uploader, description, sensitivity, media type, size, and timestamp metadata.

### Search and control reliability

- Global search now covers demands, projects, tasks, task comments, milestones, RAID, dependencies, decisions, missions, core functions, organizations, and RTM requirements.
- Search results use access-aware scoping and relevance ranking, with exact identifier matches placed first.
- Type-ahead suggestions, keyboard navigation, and a functional submit control replace the nonfunctional search behavior.
- The stray visual **K** artifact was removed while retaining Command/Ctrl+K as an invisible keyboard shortcut.
- Inline JavaScript event handlers were removed so controls work under the application Content Security Policy.

![Task workspace](docs/screenshots/11-v0.3.0-task-workspace.png)

![Expanded search results](docs/screenshots/12-v0.3.0-search.png)

The v0.6.0 interface provides two first-class themes: **Premium Enterprise Dark** is the default and **Premium Enterprise Light** is available from the top command bar. Both use the same responsive navigation, panels, fields, tables, and drill-down behavior.

## What works on the first build

After `docker compose up -d --build`, the application automatically waits for PostgreSQL, runs Alembic migrations, seeds the demonstration environment, starts the web service, and exposes health checks.

A user can immediately:

- Sign in with documented demonstration accounts.
- Open a populated DDC5I executive dashboard and six division dashboards.
- Drill from exceptions into demand, project, milestone, RAID, dependency, owner, financial, and benefit records.
- Create and submit a demand, edit the submitted version with governed revision history before assessment, move it through triage and clarification, score it, route it through stage gates, record a decision, and convert approved work into a project without rekeying.
- Use a project workspace with overview, WBS, Kanban, milestones, RAID, dependencies, actions, financials, benefits, status updates, and a detailed task drawer/full-page workspace with notes, comments, checklist, files, relationships, evidence, and audit history.
- See project status changes roll up to division and enterprise views.
- Search across all major accessible record types, use type-ahead suggestions, filter, save views, export accessible records, review notifications, and inspect material audit history.
- Upload a versioned demand workbook, preview create/update/duplicate/warning/error/permission outcomes, commit valid rows, and download a correction workbook.
- Inspect all 307 RTM requirements and filter by ID, domain, phase, preliminary fit, implementation status, release, and other traceability fields.
- Create and update local demonstration users, register acting-role delegations, and inspect audit evidence.
- Conduct a portfolio review, record a governed recommendation, and create linked decision/action records.
- Generate and inspect a ProjectOS canonical dry-run payload under explicit field-ownership rules.
- Submit and decide resource requests and append financial transaction evidence.
- Build a non-destructive scenario, calculate impacts, approve it, and apply only through a separate audited action.
- Run a data-quality scan, assign findings, generate an approved report pack, and inspect persistent job history.

No visible control is intentionally decorative. Capabilities that are not usable are documented as roadmap items instead of being presented as working buttons.

## Screenshots

> **v0.6.0 screenshot note:** The package retains historical authenticated screenshots. Capture refreshed dashboard, project, demand, resource, investment, scenario, and administration views on the target Docker host for formal publication.

### Executive portfolio dashboard

![Executive dashboard](docs/screenshots/02-executive-dashboard.png)

### Division dashboard

![Division dashboard](docs/screenshots/03-division-dashboard.png)

### Demand pipeline and governed intake

![Demand pipeline](docs/screenshots/04-demand-pipeline.png)

![Demand detail](docs/screenshots/05-demand-detail.png)

### Built-in project execution

![Project Kanban](docs/screenshots/06-project-kanban.png)

![Task workspace](docs/screenshots/11-v0.3.0-task-workspace.png)

![Project RAID](docs/screenshots/07-project-raid.png)

### Supporting decision data

![Resource capacity](docs/screenshots/08-resource-capacity.png)

![Excel import](docs/screenshots/09-excel-import.png)

![RTM administration](docs/screenshots/10-requirements-rtm.png)

![Expanded global search](docs/screenshots/12-v0.3.0-search.png)

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
| Portfolios & Projects | Six division portfolios, project conversion, execution workspace, WBS controls, Kanban, task-detail drawer, notes, comments/mentions, checklist, secure task attachments, task relationships, milestones, RAID, dependencies, status |
| Resources | Role and skill capacity, allocation, actual effort, over-allocation, minimum core-function coverage |
| Financials | ROM, approved budget, actual, forecast, variance, minimum viable, full requirement, funding status |
| Benefits | Expected/realized values, owner, status, unit, and review date |
| Collaboration | In-app notifications, assignments, workflow updates, persistent task comments and @mentions, task notes/evidence, local Mailpit option |
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

Validated in the release workspace: **60 tests passed**. The v0.5.0 application-code coverage baseline was 83%. Coverage includes scoring, permissions, stage transitions, database uniqueness, import validation, audit evidence, health checks, critical routes, accessible landmarks, division access denial, auditor read-only behavior, project status roll-up, the full demand-to-project workflow, the v0.6.0 dashboard, requested navigation, theme defaults, and legacy-route removal.

The build environment used to create this package did not include the Docker CLI or daemon, so the Compose stack was structurally validated but not launched here. Run the documented Docker health check on the target Docker Desktop host; this limitation is explicitly recorded in the acceptance checklist.

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
- File extension, name, path, size, SHA-256, and lightweight binary-signature controls in the storage adapter
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

The database-backed integration and field-ownership registry prevents ambiguous ownership by design. v0.5.0 includes a ProjectOS canonical-payload dry run and persisted synchronization evidence; it does not make a live remote call. ServiceNow SPM, Microsoft Graph, SharePoint, Advana/WDP, Power BI, Jira, Azure DevOps, financial systems, workforce systems, and enterprise identity remain adapter/integration work rather than hidden MVP dependencies.

## Requirements traceability

- In-app route: **Requirements RTM**
- Machine-readable source: `app/data/requirements.json`
- Exported status report: [`docs/DDC5I_RTM_MVP_Status.csv`](docs/DDC5I_RTM_MVP_Status.csv)
- Narrative report: [Requirements Traceability](docs/REQUIREMENTS_TRACEABILITY.md)

Status is intentionally conservative. An RTM row is marked Implemented only when the reference MVP contains a usable vertical slice and a design/module reference. “Requires integration” and “Requires policy or governance decision” remain explicit.

## Roadmap

The five-phase roadmap is in [ROADMAP.md](docs/ROADMAP.md). Each roadmap work package includes business value, dependencies, related requirement IDs, complexity, primary owner, acceptance criteria, security implications, integration implications, and recommended release.

The recommended next release is **0.6.0 — Connected Operations and Workforce/Investment Depth**, centered on a live authenticated ProjectOS test connector, OIDC enterprise identity, delegated-role authorization enforcement, durable background workers, SharePoint/Graph document and notification adapters, detailed workforce calendars, multi-year investment profiles, scenario propagation, and reconciliation dashboards. AI remains gated until access control, data quality, metrics, lineage, audit, evaluation, and human-review controls are demonstrably mature.

## Documentation index

- [Target Operating Model](docs/TARGET_OPERATING_MODEL.md)
- [Installation Guide](docs/INSTALLATION.md)
- [Upgrade to v0.6.0](docs/UPGRADE_0.6.0.md)
- [Prior upgrade to v0.5.0](docs/UPGRADE_0.5.0.md)
- [Upgrade to v0.4.0](docs/UPGRADE_0.4.0.md)
- [Reverse Proxy and Rate-Limit Configuration](docs/REVERSE_PROXY.md)
- [Upgrade to v0.3.1](docs/UPGRADE_0.3.1.md)
- [Upgrade to v0.3.0](docs/UPGRADE_0.3.0.md)
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
