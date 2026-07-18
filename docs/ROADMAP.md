# Product Roadmap

## Delivered in v0.5.0 — Portfolio Governance and Enterprise Integration

- Local user administration with multiple roles, division scope, sensitive-record access, activation/deactivation, and audit.
- Acting-role delegation registry with roles, organization scope, effective dates, rationale, and audit evidence.
- Portfolio-review forum with agenda items, recommendations, linked decisions, linked actions, and completion evidence.
- Integration connection registry, field-ownership rules, health status, synchronization history, and ProjectOS canonical dry run.
- Resource-request submission and approval/decline workflow.
- Financial transaction evidence for commitments, obligations, expenditures, and related planning entries.
- Non-destructive portfolio scenarios with calculate, approve, and separately governed apply.
- Data-quality command center with scans, assignment, due dates, disposition, and resolution.
- Source-grounded report packs and persistent job-history evidence.
- Expanded global search and RTM evidence for the new records.

## Recommended v0.6.0 — Connected Operations and Workforce/Investment Depth

| Work package | Business value | Dependencies | Requirement anchors | Complexity | Primary owner | Acceptance criteria | Security implications | Integration implications | Recommended release |
|---|---|---|---|---:|---|---|---|---|---|
| OIDC enterprise identity adapter | replaces local demonstration authentication while retaining stable internal users | enterprise IdP metadata, claims mapping, network/accreditation | SEC-001–010, ORG-001–010 | XL | Identity Owner + Platform Admin | sign-in, sign-out, role/scope claims, account linking, break-glass local admin, audit, and documented failure modes | MFA, token validation, session policy, privileged access | OIDC first; SAML/CAC/PIV through approved enterprise broker | 0.6.0 |
| Enforced acting-role delegation | makes temporary authority operational rather than registry-only | delegation policy, SoD rules, approval authority | ORG-007, ADM-005, SEC-004 | L | Platform Admin + Security Reviewer | active/effective delegation augments only approved roles/scope; expired/revoked access stops immediately; audit identifies acting authority | privilege escalation, dual control, emergency access | identity claims remain distinct from application delegation | 0.6.0 |
| Live ProjectOS test connector | removes duplicate task/milestone entry in a governed test environment | ProjectOS API, credentials, canonical mapping, field ownership | DAT-009–021, PRJ-021–022 | XL | Integration Owner + PMO | authenticated send/read, idempotency, retries, conflict queue, reconciliation, dry run, operator resolution, lineage | service identity, secret vault, project scope | first live bidirectional connector | 0.6.0 |
| Durable jobs and notification worker | makes recurring scans, reports, imports, retries, and digests reliable | approved queue/store and operations policy | COL-010–013, ADM-009–013, DAT-016–019 | XL | Platform Operations | persistent schedules, worker health, retry/backoff, dead letter, replay, cancellation, and audit | queue authorization, replay prevention, sensitive payload minimization | supports all future connectors | 0.6.0 |
| Microsoft Graph and SharePoint pilot | connects approved email/calendar/document workflows without making them mandatory | Entra app registration, tenant consent, library/list governance | COL-006–013, SEC-012–019, DAT-009–021 | XL | Collaboration + Records Owners | authenticated deep links, minimal email, calendar event, controlled document link, version/metadata, reconciliation and failure queue | token/tenant controls, external recipients, DLP, records | Graph and SharePoint adapters | 0.6.0 |
| Detailed workforce planning | turns role-hour requests into time-phased supply/demand and coverage decisions | skill taxonomy, calendars, approved workforce source | RES-001–022 | XL | Resource Manager | monthly capacity, allocations, vacancies, contractors, skill/proficiency, over-allocation resolution, core-function minimum coverage | workforce privacy, field-level restrictions | workforce/calendar feed and ProjectOS actual effort | 0.6.0 |
| Multi-year investment management | provides credible funding lifecycle and EAC decision support | financial taxonomy, fiscal calendar, official source agreement | FIN-001–015, VAL-013–026 | XL | Financial Manager | funding source, budget, commitment, obligation, expenditure, forecast/EAC, multi-year profile, variance, underfunding and reconciliation | financial field restrictions, audit, data minimization | financial-system ingestion and write ownership | 0.6.0 |
| Scenario propagation and staleness | makes what-if results trustworthy across dependencies and changing baselines | schedule/dependency/resource models | SCN-001–016 | XL | Portfolio Analytics Lead | stale scenarios flagged; recalculation required; schedule, resource, funding, risk and benefit impacts propagate with explanations | scenario confidentiality and approval separation | reads ProjectOS/workforce/financial feeds | 0.6.0 |
| Reconciliation command center | gives operators one place to resolve connector and data conflicts | live connectors, ownership rules, durable jobs | DAT-009–021, ADM-009–013 | XL | Data Steward + Integration Owners | conflicts assigned, compared, resolved, retried, closed, measured by SLA, and fully audited | sensitive before/after values and privileged resolution | cross-connector control plane | 0.6.0 |
| Signed report packages and archive | produces durable approved leadership products | report templates, records decision, document service | DSH-013–020, COL-010, SEC-012–019 | L | PMO + Records Manager | scheduled pack, approved source snapshot, signed/locked version, PDF/XLSX, distribution history, archive and retrieval | markings, distribution controls, retention | SharePoint/records repository | 0.6.0 |

# Five-Phase Product Roadmap

The roadmap keeps the original five-phase strategy while showing which usable slices are delivered and which require enterprise decisions or connections.

## Phase 1 — Foundation and Usable MVP

**Delivered through v0.1.0–v0.3.1:** organization and RBAC, mission/core-function catalog, demand funnel, assessment/scoring, stage gates, decisions, portfolio/project initiation, execution workspace, dashboards, basic resources/financials/benefits, Excel import/export, notifications, audit, RTM, reliable task details, governed submitted-demand revision, and scoped search.

Remaining hardening: enterprise identity, formal access certification, approved records storage, browser/accessibility certification, and operational security evidence.

## Phase 2 — Portfolio and Execution Expansion

**Delivered through v0.4.0–v0.6.0:** configurable boards/WIP, WBS hierarchy, scheduling/baseline/basic critical path/Gantt, versioned task evidence, project blueprints, governed status reports and reporting roll-up, portfolio roadmaps, portfolio review forum, review decisions/actions, report-pack snapshots, and the premium responsive application shell.

Remaining expansion: advanced calendars, lag/lead, resource leveling, portfolio critical path, blueprint authoring/approval lifecycle, signed recurring report packages, and calendar/meeting integration.

## Phase 3 — Resource and Financial Management

**Usable v0.5.0 foundation:** role/skill/hour resource requests, approval/decline, capacity summaries, financial baselines, transaction evidence, budget/forecast/actual/variance, funding gaps, and benefits.

Next: named/person/team calendars, proficiency/vacancies/contractors, assignment approval, planned-versus-actual effort, core-function protected minimums, multi-year funding, official commitments/obligations/expenditures, EAC, ROI, and source-system reconciliation.

## Phase 4 — Forecasting and Enterprise Integration

**Usable v0.5.0 foundation:** non-destructive scenario changes/results/approval/apply, integration registry, field ownership, health state, synchronization history, ProjectOS canonical dry run, data-quality issue workflow, and job evidence.

Next: live ProjectOS test connector, durable events/retries/dead letter, Microsoft 365/SharePoint, workforce/financial feeds, scenario propagation, full reconciliation center, Advana/WDP/Power BI data products, and optional Jira/Azure DevOps adapters.

## Phase 5 — Optimization and Responsible AI

AI remains gated. Future capabilities may include forecast-accuracy analysis, early warnings, decision-latency analysis, explainable resource/portfolio recommendations, duplicate-demand detection, and source-linked draft summaries only after:

- authoritative source ownership and reconciliation are operational
- access control and delegated authority are proven
- data quality and lineage meet approved thresholds
- model/version/evaluation/feedback/rollback controls exist
- every generated claim links to permitted source records
- human review and approval are mandatory and audited

## Release sequencing

1. **v0.5.1**, only if target-host acceptance identifies blocking defects.
2. **v0.6.0**, connected operations, identity, durable jobs, detailed workforce/investment, and scenario propagation.
3. **v0.7.0**, enterprise analytics/data products, records lifecycle, advanced portfolio optimization, and broader reconciled integrations.
4. Responsible AI pilot only after governance gates are met.
