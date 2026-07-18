
## v0.5.0 additions

| Capability | Status | Operational result | Transparent boundary |
|---|---|---|---|
| Local user administration | Implemented for demonstration | Create/update users, multiple roles, division scope, sensitive access, activation state, audit | Not enterprise provisioning, access certification, OIDC/CAC/PIV |
| Acting-role delegation registry | Partially implemented | Stores roles, scope, dates, reason, status, creator, audit | Delegated roles not yet enforced in every authorization check |
| Portfolio-review forum | Implemented | Review period, chair/participants, agenda items, recommendations, linked decisions/actions, completion | Calendar/signature/minutes package integration planned |
| Integration connection registry | Partially implemented | Connection metadata, mode, auth type, enabled/status, health evidence | Live credentialed connections require target environment |
| Field-ownership rules | Implemented as governance data | Authoritative system, allowed writers, conflict policy | Enforcement against live adapters begins when adapters are enabled |
| ProjectOS canonical dry run | Partially implemented | Project/task/milestone payload, record counts, result and sync audit | No remote network call or bidirectional reconciliation |
| Resource-request workflow | Implemented baseline | Submit, prioritize, approve/decline, resolution, audit | Not authoritative people/position assignment |
| Financial transaction register | Implemented baseline | Commitment/obligation/expenditure-like evidence with source/reference/date/amount | Not official accounting or funds-control posting |
| Non-destructive scenarios | Implemented baseline | Draft changes, calculate results, approve, separate apply, before/after audit | Limited fields; no propagation/optimization/staleness invalidation |
| Data-quality command center | Implemented baseline | Scan, persist issue, owner, due date, disposition, resolve, job evidence | Fixed deterministic rules; no federated rule catalog |
| Report packs | Implemented baseline | Source-derived sections/narrative, period/org, approve, job evidence | No durable scheduler, signed PDF, or distribution adapter |
| Operations job history | Partially implemented | Persistent job status/payload/result/error evidence | No distributed worker, retry daemon, dead-letter queue |
| Expanded search | Implemented | Search reviews, scenarios, quality issues, report packs, resource requests with access controls | No attachment-body or semantic/federated search |

# Feature Inventory — v0.5.0

## Implemented and usable

### Platform

- Dockerfile and Docker Compose for PostgreSQL 16, web application, and Mailpit
- Alembic migrations through `0004_execution_roadmap_v040`
- idempotent demonstration seed
- live/readiness health endpoints
- local file-storage, integration, and background-job interfaces
- authenticated OpenAPI document

### Identity and access

- local demonstration login with PBKDF2 password hashing
- signed HTTP-only session cookie and CSRF validation
- server-side role checks, enterprise/division scope, sensitive-record access, and auditor read-only behavior
- login attempt throttling and audit evidence

### UX themes and navigation

- Premium Enterprise Dark default interface
- Premium Enterprise Light alternate interface
- portfolio overview with leadership KPIs and direct authoritative drill-downs
- collapsible navigation, responsive layout, breadcrumbs, command bar, filters, and saved views
- CSP-compatible event handling for theme, navigation, confirmations, print, Kanban, and task drawer
- versioned local CSS/JavaScript URLs to prevent stale browser bundles after upgrade

### Search

- access-aware search across demands, projects, tasks, task comments, milestones, RAID, dependencies, decisions, missions, core functions, organizations, and requirements
- exact-identifier relevance priority
- type-ahead suggestions and keyboard navigation
- result-type filters and direct authoritative-record links
- Command/Ctrl+K shortcut without a visible keyboard-label artifact

### Strategy, demand, assessment, and decisions

- DDC5I Enterprise plus six divisions
- mission and core-function catalogs
- guided demand draft/submit/triage/clarification/assessment/recommendation/decision lifecycle
- governed editing of eligible Submitted and Clarification Required demands with optimistic version checks, change summaries, revisions, audit, notifications, and post-assessment locking
- weighted scoring, rationale, confidence, multiple assessors, variance, comparison, mandatory overrides
- stage gates, decision evidence, capacity tradeoff, conditions/actions
- approved demand conversion to a linked project without rekeying

### Portfolio and project execution

- six division portfolios and project inventory
- owner/calculated/override project health and status updates
- WBS list with unique IDs, sequence, move up/down, indent/outdent, due-date baseline, effort, progress, and in-place detail opening
- Kanban board with authorized drag-and-drop status/column movement
- milestones, RAID, cross-project dependencies, decisions, actions, financials, benefits, and source drill-down

### Detailed task workspace

- right-side popup/drawer opened from Kanban and WBS
- real full-page task links and a shareable authoritative task route when JavaScript or panel loading is unavailable
- title, description/acceptance criteria, status, board column, priority, owner, contributors, start/due/baseline dates
- estimated/actual effort, percent complete, tags, persistent working notes, and acceptance evidence
- checklist create/toggle/reopen/delete
- comments with `@username` notifications
- finish-to-start, start-to-start, finish-to-finish, and related task relationships
- task audit history and linked RTM requirements

### Task files and evidence

- upload, download, and authorized deletion
- PDF, DOCX, XLSX, PPTX, CSV, TXT, Markdown, JSON, PNG, JPG, and JPEG allow-list
- configured file-size limit, secure filenames, safe storage keys, lightweight binary-signature validation, media type, sensitivity, SHA-256 hash, uploader, timestamp, and access checks
- Docker-volume persistence

### Resources, finance, value, dashboards, and reports

- role/skill capacity, allocation, actual effort, utilization, coverage, and over-allocation warnings
- budget, actual, forecast, variance, funding status, minimum viable and full requirement
- benefit target/realized register
- executive and six division dashboards, demand pipeline, exceptions, milestones, dependencies, stale data, and source-grounded narrative
- notifications, My Work, CSV export, print-ready reports

### Import, traceability, and audit

- versioned workbook with eight template sheets
- demand preview/commit/correction with row-level outcomes and source lineage
- 307 RTM records with filters, detail profiles, reverse links, design/module/test/release evidence
- material before/after audit events

## Partially implemented

- organization and role configuration: relational model exists; complete administration UI is absent
- conditional intake and workflow configuration: usable workflow exists; form/workflow designer is absent
- WBS and schedule: hierarchy, baselines, Gantt layout, cycle detection, and a basic critical path exist; calendars, resource leveling, schedule import, and multiple authorized baseline versions remain incomplete
- Kanban: configurable columns, ordering, criteria, archival, drag-and-drop, and server-enforced WIP exist; swimlanes, flow analytics, bulk operations, and keyboard reordering remain incomplete
- document management: task versioning, safe preview, download audit, soft deletion, and restoration work; full-text indexing, malware scanning, DLP/CDR, legal hold, disposition, and repository integration remain absent
- task dependencies: relationships persist, finish-to-start cycles are rejected, and basic critical path is calculated; complete constraint propagation, lag/lead, calendars, and resource leveling remain absent
- collaboration: task comments/mentions work; universal threaded discussions and resolution workflow are incomplete
- notifications: in-app works; digest and Graph/SMTP delivery remain roadmap
- project status roll-up: project/milestone/RAID/dependency/finance/benefit data roll up; full task/resource actual aggregation needs expansion
- portfolio roadmaps and baselines: a portfolio roadmap and task/project baseline fields exist; authorized portfolio baseline snapshots, change control, and interactive scenarios remain absent
- narrative and report packs: governed project status reports support versioned reporting periods, approval, enterprise reporting roll-up, and print/PDF; scheduled recurring generation and enterprise report-pack approval remain absent

## Planned, integration-dependent, governance-dependent, or deferred

See the in-app RTM, `DDC5I_RTM_MVP_Status.csv`, Known Limitations, and Roadmap. Major areas include enterprise identity, user lifecycle, advanced schedules/Gantt, project blueprints, approved records management, detailed workforce and finance, durable jobs, ProjectOS/ServiceNow/Microsoft/Advana/WDP integrations, scenarios/optimization, and responsible AI.

## v0.4.0 additions

| Capability | Status | Key evidence |
|---|---|---|
| Trusted proxy and client-aware rate limit | Implemented for fixed-hop local deployment | `app/main.py`, `docs/REVERSE_PROXY.md`, `tests/test_v040.py` |
| Configurable project boards and WIP | Implemented baseline | `BoardColumn`, board configuration routes/UI, WIP tests |
| WBS hierarchy and baseline actions | Implemented baseline | task parent/indent/sequence/baseline actions |
| Basic critical path and Gantt | Implemented baseline | `app/services/schedule.py`, Schedule tab |
| Portfolio roadmap | Implemented baseline | `/roadmaps` |
| Task note revisions | Implemented | `TaskNoteRevision`, task workspace |
| Attachment versioning/preview/restore | Implemented baseline | `TaskAttachment` version fields and routes |
| Project blueprints | Implemented baseline | `ProjectTemplate`, `/templates` |
| Governed recurring status reports | Implemented baseline | `StatusReport`, project Status tab, reporting views |
| Blueprint provenance | Implemented | `Project.template_code`, `Project.template_version` |
