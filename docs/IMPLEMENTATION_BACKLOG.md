# Implementation Backlog by Vertical Slice

The backlog follows the requested delivery order and keeps the repository runnable after every iteration. Items marked Done are present through release 0.5.0; Partial means a usable subset exists; Next/Planned remain transparent.

## Iteration 1 — Foundation

| Item | Status | Acceptance evidence |
|---|---|---|
| Docker Compose with PostgreSQL, web, Mailpit | Done | compose file, health checks, named volumes |
| Automated migration and seed | Done | entrypoint, Alembic revision, idempotent seed |
| Local demonstration authentication | Done | PBKDF2, signed cookie, demo accounts |
| RBAC, division scope, sensitive records | Done | server checks and automated denial tests |
| Organization hierarchy | Done | DDC5I plus six configurable divisions |
| Application shell and navigation | Done | responsive left nav, command bar, search, theme |
| Audit event foundation | Done | material before/after records |
| Production enterprise identity adapter | Planned | OIDC/SAML/CAC/PIV integration decision required |

## Iteration 2 — Strategy and Demand

| Item | Status | Acceptance evidence |
|---|---|---|
| Mission and core-function catalog | Done | strategy page and bidirectional counts |
| Guided demand intake | Done | draft/submit form and validation |
| Full configurable conditional-question engine | Planned | Phase 2 schema/versioning |
| Triage and clarification | Done | stage transitions and pending information |
| Demand revision history | Done | version snapshot and comments |
| Sensitivity and restricted intake | Done | permission checks and seeded record |
| Attachments and evidence lifecycle | Partial | storage adapter exists; full UI/records integration next |
| Co-author editing and mentions | Planned | collaboration work package |

## Iteration 3 — Assessment and Decisions

| Item | Status | Acceptance evidence |
|---|---|---|
| Weighted model and score rationale | Done | 100-point calculation and tests |
| Multiple assessors and variance | Done | assessment history and variance |
| Side-by-side comparison | Done | assessment comparison route |
| Mandatory-work override fields | Partial | seed/model/UI visibility; admin configuration next |
| Stage gates | Done | governed lifecycle transitions |
| Leadership decision record | Done | disposition, authority, evidence, implications |
| Decision conditions to actions | Done | one action per condition line |
| Capacity tradeoff control | Done | approval beyond capacity validation |
| Configurable scoring models in database | Planned | remove code-defined weight dependency |
| Formal portfolio recommendation record | Partial | gate/state exists; normalized recommendation next |

## Iteration 4 — Portfolio and Projects

| Item | Status | Acceptance evidence |
|---|---|---|
| Six division portfolios | Done | seeded and linked |
| Demand-to-project conversion | Done | no-rekey test |
| Project overview and status | Done | owner health, progress, narrative, roll-up |
| WBS/task list | Done baseline | hierarchical numbering, parent tasks, sequence/indent, baseline and task workspace |
| Kanban | Done for MVP | configurable field and drag/move API |
| Milestones | Done for MVP | confidence, critical, baseline/current dates |
| RAID and dependencies | Done for MVP | table views, ownership, severity, due date |
| Full schedule engine/critical path | Partial | basic finish-to-start path/Gantt delivered; calendars, lag/lead, leveling next |
| Document and acceptance-evidence repository | Partial | model fields/storage contract; full UI next |
| Project closure checklist and lessons workflow | Planned | Phase 2 |
| ProjectOS synchronization registry | Partial | database registry, field ownership, sync history and canonical dry run; live adapter planned |

## Iteration 5 — Dashboards and Reports

| Item | Status | Acceptance evidence |
|---|---|---|
| Executive dashboard | Done | exception metrics, source drill-down |
| Six division dashboards | Done | mission/function/project/capacity/financial views |
| Metric definitions and limitations | Done | metric governance detail |
| Saved filters/views | Done for MVP | user route/query saved view |
| Reports and browser print | Done for MVP | reporting screen, CSV, print-ready route |
| Editable generated narrative | Partial | source-grounded narrative, editing next |
| Recurring report packs | Partial | source-grounded pack generation/approval/job evidence; scheduler/distribution next |
| Power BI / WDP data product | Requires integration | governed analytics feed |

## Iteration 6 — Supporting Capabilities

| Item | Status | Acceptance evidence |
|---|---|---|
| Role/skill resource capacity | Done for MVP | utilization and coverage warnings |
| Detailed workforce module | Planned/integration | people, position, skill, vacancy, contractor data |
| Basic financial planning | Done for MVP | budget, actual, forecast, variance, funding |
| Detailed investment ledger | Partial/integration | transaction evidence delivered; official commitments/obligations/expenditures/EAC require source integration |
| Benefit register | Done for MVP | target/realized/status/owner |
| In-app notifications | Done | submission/workflow/approval links |
| Mailpit option | Done infrastructure | SMTP capture container; notification sender enhancement next |
| Excel demand preview and commit | Done | row-level outcomes and correction download |
| Seven additional import contracts | Done template; commit planned | versioned workbook sheets |
| RTM administration | Done | all 307 rows and status updates |
| Data-quality views | Done baseline | persistent deterministic scans, issue ownership/due date/disposition/resolution and job evidence |

## Iteration 7 — Hardening

| Item | Status | Acceptance evidence |
|---|---|---|
| Unit/integration/end-to-end tests | Done baseline | 57 passing tests; 83% application-code coverage |
| Accessibility landmarks and keyboard-oriented UI | Done baseline | automated landmark checks; formal audit pending |
| Security review and headers | Done baseline | CSRF, CSP, role/scope checks, rate limiting |
| Performance review | Planned | representative load and query plans |
| Backup/restore scripts | Done | PostgreSQL scripts and guide |
| Comprehensive documentation | Done | README and role/admin/security/roadmap guides |
| Screenshots | Done | ten major views |
| Release package and acceptance checklist | Done | ZIP and documented evidence |
| Docker daemon execution in build environment | Not available | must be validated on target Docker Desktop host |
| Formal UAT, accessibility, security and RMF evidence | Not run | owner acceptance required |

## Iteration 8 — v0.5.0 Portfolio Governance and Enterprise Integration

| Item | Status | Acceptance evidence |
|---|---|---|
| Local user lifecycle | Done for demonstration | create/update/activate/deactivate, roles, scope, sensitive access, audit |
| Acting-role delegation | Partial | dated/scoped/audited registry; authorization enforcement next |
| Portfolio review forum | Done baseline | agenda items, recommendations, linked decisions/actions, completion |
| Integration control plane | Partial | connection, ownership, health, sync-run history; live credentials/reconciliation next |
| ProjectOS adapter | Partial | canonical project/task/milestone dry run; no remote write |
| Resource-request workflow | Done baseline | submit, decide, resolution, audit |
| Financial transaction evidence | Done baseline | stable planning/evidence entries linked to financial records |
| Scenario workspace | Done baseline | non-destructive changes, calculate, approve, separate apply, audit |
| Data-quality command center | Done baseline | scan, assign, disposition, resolve, job evidence |
| Report packs and operations | Partial | source-grounded generation/approval and persistent job history; durable scheduler/distribution next |
| Expanded search/RTM | Done baseline | new record types searchable; conservative 307-row evidence update |

## Next vertical slices — v0.6.0

1. OIDC enterprise identity and enforced delegated authority.
2. Live authenticated ProjectOS test connector with retries, idempotency, reconciliation, and conflict resolution.
3. Durable worker/scheduler and notification/report distribution.
4. Microsoft Graph/SharePoint pilot with records and security governance.
5. Detailed workforce calendars, skills, vacancies, contractors, and core-function coverage.
6. Multi-year investment lifecycle, EAC, and official financial reconciliation.
7. Scenario staleness, dependency/schedule/resource propagation, and reconciliation command center.
