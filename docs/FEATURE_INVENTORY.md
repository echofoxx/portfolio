# Feature Inventory — v0.8.3

## Executive Travel Assurance & Theme Refinement

| Capability | Status | Operational result | Transparent boundary |
|---|---|---|---|
| Professional themes | Implemented | Nine persistent token-based themes preserve layout and semantic status colors | Local browser preference; not centrally managed branding |
| Clean form presentation | Implemented | Injected Input Area boxes are removed; field labels and validation remain | Does not change authorization or validation rules |
| Blueprint Catalog control | Implemented | Concise single-line catalog access aligns under blueprint selection | Blueprint authoring remains code/seed governed |
| Location compliance aggregation | Implemented | Completed required travel reconciles to linked and overdue reports per location | Linkage does not certify report content quality |
| Executive travel map | Implemented | One linked map/index/detail system shows spend, completion, gaps, unmapped exposure, and source drill-through | Marker view only; country/AOR/time/heat are Phase 2 |
| Direct interaction | Implemented | Mouse, trackpad, touch/pinch, double-click, and keyboard pan/zoom with filtered fit | Formal target-device certification remains UAT work |

## Platform release status

- Application version: 0.8.3.
- Migration head: `0009_self_service_v080` (unchanged).
- 115 automated tests pass.
- No new runtime dependency or database schema change.

---

# Historical Feature Inventory — v0.8.2

## Executive Demo Readiness Hotfix

| Capability | Status | Operational result | Transparent boundary |
|---|---|---|---|
| Complete RAID identity | Implemented | Full identifiers remain visible and metadata remains single-line | Long narrative fields alone are intended to wrap |
| Grouped input guidance | Implemented | Board Governance and Travel place guidance above the whole editable area | Guidance does not replace field validation or authorization |
| Executive dashboard grids | Implemented | Six KPIs and eight divisions align evenly with responsive breakpoints | User panel personalization remains governed by size tokens |
| Navigable task breadcrumbs | Implemented | All focused-task breadcrumb targets return HTML and the task collection returns to Board | Breadcrumbs do not retain unsaved form state |
| Compact/mobile shell controls | Implemented | Icon control aligns predictably and sidebar Sign out stays available | Sign out remains a POST with CSRF protection |
| Regional travel map | Implemented | Region and measure lenses, zoom/fit, clustering, summary, URL state, and linked source navigation | Local city-level reference points are not routes or authoritative geospatial intelligence |

## Platform release status

- Application version: 0.8.2.
- Migration head: `0009_self_service_v080` (unchanged).
- 111 automated tests pass.
- No new runtime dependency or database schema change.

---

# Historical Feature Inventory — v0.8.1

## Responsive Portfolio Presentation Hotfix

| Capability | Status | Operational result | Transparent boundary |
|---|---|---|---|
| Structured project overview | Implemented | Purpose, end state, scope, deliverables, accountability, schedule variance, completion, and project signals render in stable layouts | Completeness still depends on record-owner input |
| Readable Gantt labels | Implemented | WBS, task title, and dates occupy separate label regions | Large schedules retain contained horizontal timeline scrolling |
| Responsive RAID | Implemented | Panels stack, metadata remains one line, narrative wraps, and mobile rows become record cards | Enterprise-wide RAID register retains its existing table behavior |
| Dedicated governance entry | Implemented | Create and Cancel are isolated from the briefing register | Permissions and required division scope remain enforced |
| Roadmap filter alignment | Implemented | Status, Division, Apply, and Reset remain visually separated from forecast content | Timeline scale remains based on accessible matching projects |
| Uniform dashboard sizes | Implemented | Compact, Standard, and Wide tokens work consistently across configurable panels | Freeform pixel placement remains intentionally excluded |
| Dedicated Investment Flow | Implemented | Dashboard summary opens a filtered, accessible, source-linked full analysis page | Planning evidence is not an authoritative accounting statement |

## Platform release status

- Application version: 0.8.1.
- Migration head: `0009_self_service_v080` (unchanged).
- 104 automated tests pass.
- No new runtime dependency or database schema change.

---

# Historical Feature Inventory — v0.8.0

## Self-Service Portfolio Operations

| Capability | Status | Operational result | Transparent boundary |
|---|---|---|---|
| User-created projects | Implemented | Authorized users create Division Local or Portfolio Managed work from a governed blueprint | It does not bypass project-role, division, or sensitivity authorization |
| Stable-ID promotion | Implemented | Local work can request and receive portfolio governance while retaining history and relationships | Approval is application governance, not funds certification |
| Role dashboard lenses | Implemented | Eight role defaults plus persistent user panel order, size, and visibility | Panels move within a smart grid; freeform pixel placement is intentionally excluded |
| Direct divisions | Implemented | Main navigation, switcher, dashboard shortcuts, and breadcrumbs lead directly to eight divisions | Access continues to follow role and organization scope |
| CCD/FO/JFID identity | Implemented | New CCD and FO profiles/banners and corrected JFID banner/summary | Source-master rights and imagery approval remain external governance |
| Focused form pages | Implemented | Primary project/resource create workflows use dedicated pages | Small configuration and approval actions may remain contextual |
| Resource exchange | Implemented | Admin template/export/preview/commit with row findings and audit | Not a live HR/workforce integration; CSV is for controlled seeding/correction |
| Expanded blueprints | Implemented | 14 versioned types instantiate boards, tasks, and milestones | Template authoring/version approval is still code/admin governed |

## Platform release status

- Application version: 0.8.0.
- Migration head: `0009_self_service_v080`.
- 97 automated tests pass.
- Clean seed: eight divisions and fourteen active project blueprints.

---

# Historical Feature Inventory — v0.7.7

## Visual Portfolio Intelligence

| Capability | Status | Operational result | Transparent boundary |
|---|---|---|---|
| Interactive travel map | Implemented | Local world outline, proportional estimate markers, keyboard selection, linked detail, and location-filter drill-through | City-level reference coordinates are stewarded locally; no route tracking or live map service |
| Location normalization | Implemented | Known aliases and typographical variants roll up to canonical destinations; mapping coverage and unmapped values are visible | Original source strings remain unchanged; unresolved values require stewardship |
| Travel visual analytics | Implemented | Monthly cost/volume, determination by division, outcome funnel, report compliance, and engagement impact share the filtered source population | Costs remain approval estimates |
| Investment Flow Sankey | Implemented | Approved budget flows through category, division, project, and actual or remaining approved outcomes with reconciliation | It is not an authoritative cash-flow statement |
| Flow drill-through | Implemented | Nodes open filtered financial baselines or source projects; accessible category table is included | Cross-system financial reconciliation remains integration-dependent |
| Briefings label | Implemented | Navigation and page labels are simplified to Briefings | Stable `/portfolio-reviews` routes and governance semantics remain unchanged |
| Accessible/local visuals | Implemented | Same-origin JavaScript, local map asset, keyboard labels, linked-list/table alternatives, and no-JavaScript source access | Formal WCAG certification remains required |

## Platform release status

- Application version: 0.7.7.
- Migration head: `0008_travel_engagements_v076` (no schema migration required for v0.7.7).
- 335 RTM rows, including ten v0.7.7 visualization, traceability, accessibility, and security requirements.
- Automated regression and v0.7.7 acceptance coverage are included in `tests/test_v077.py`.
- v0.7.6 travel lifecycle, v0.7.5 division experience, and v0.7.0 briefing governance remain available.

---

# Historical inventory — v0.7.6

## Travel & Engagement Outcomes

| Capability | Status | Operational result | Transparent boundary |
|---|---|---|---|
| Travel approval import | Implemented | Controlled XLSX validation, preview, commit, stable IDs, row/file provenance, raw payload, and audit evidence | Approval-source values are not authoritative actual expenditures |
| Trip-report import | Implemented | Complete purpose, discussion, findings, recommendations, and action narratives are retained | Narrative sensitivity review does not replace authoritative classification |
| Engagement consolidation | Implemented | Multiple traveler requests and divisions roll up to a reusable event/forum/exercise record | Alias merge/split administration is not yet configurable in the UI |
| Request/report reconciliation | Implemented | Candidate scores use traveler, division, date, event title, and location with human confirmation and clear/rematch | Fuzzy matching remains review evidence, not an authoritative join |
| Travel dashboard | Implemented | Estimate/status/month/division/location/compliance views drill to contributing records | Location presentation is local; no live map/geocoding service is called |
| Trip-report review | Implemented | Status, comments, reviewer, timestamp, and audit evidence support governed review | Electronic signature and external records archive are not included |
| Structured outcomes | Implemented | Findings, recommendations, actions, risks, decisions, and dependencies are reviewable independently | Automated text extraction is deterministic and requires human disposition |
| Portfolio promotion | Implemented | Outcomes become canonical Actions, RAID risks, Decisions, or Dependencies with clickable source backlinks | Promotion does not silently modify the historical report narrative |
| Division and briefing integration | Implemented | Division Portfolio and sixteen-section briefing show period-specific travel outcomes and follow-through | Standard briefing sensitivity exclusions still apply |
| Search, My Work, quality, export | Implemented | Travel records appear in search, follow-up queues, data-quality scans, CSV exports, and division packages | Scheduled reminders and external distribution require future workers/connectors |

## Platform release status

- Application version: 0.7.6.
- Migration head: `0008_travel_engagements_v076`.
- 325 RTM rows, including twelve v0.7.6 requirements.
- 77 automated tests pass.
- Clean seed: 385 requests, $1,082,395.25 approval estimate, 9 trip reports, and one retained date anomaly warning.
- v0.7.5 division banners/profiles and v0.7.0 briefing/review capabilities remain available.

---

# Historical inventory — v0.7.5

## Division Experience and Data Exchange

| Capability | Status | Operational result | Transparent boundary |
|---|---|---|---|
| Division banner identity | Implemented | Six responsive, accessible, optimized division banners render on the division index and detail views | Source image master management remains outside the application |
| Canonical division view | Implemented | Current and briefing modes use the same source-backed page with presentation support | The separate 15-section review workspace remains available for governed preparation and interaction |
| Governed division profile | Implemented | Mission, vision, focus, responsibilities, branches, initiatives, relationships, forums, doctrine, sources, and banner metadata are maintained per division | Profile approval is role-gated but does not yet use a separate multi-step content approval workflow |
| Authoritative division naming | Implemented | CID is Coalition Interoperability Division; JFID and C3OD2 names are corrected without changing stable codes or IDs | Historical external documents are not rewritten |
| JSON division export | Implemented | Versioned package includes accessible profile and live portfolio entities | Export is a point-in-time application package, not a signed records artifact |
| CSV division export | Implemented | ZIP package provides separate profile, project, demand, core-function, capacity, financial, milestone, and RAID CSV files | Relationship-rich records are flattened for tabular use |
| JSON/CSV profile import | Implemented | Authorized users preview, validate, and explicitly publish profile changes with audit evidence | v0.7.5 does not bulk-import project, demand, resource, financial, milestone, or RAID data |
| Profile stewardship permissions | Implemented | Admin, PMO, enterprise portfolio owner, data steward, division chief, and division portfolio manager roles can maintain profiles within scope | Enterprise identity and formal access certification remain future work |

## Platform release status

- Application version: 0.7.5.
- Migration head: `0007_division_experience_v075`.
- 313 RTM rows, including six v0.7.5 division-experience and data-exchange requirements.
- 72 automated tests pass.
- v0.7.0 briefing lifecycle, snapshots, interactive review, questions, changes, actions, and closeout remain available.
- v0.6.1 role guidance, display preferences, and process orientation remain available.

---

# Feature Inventory — v0.7.0

## Division Briefing & Review

| Capability | Status | Operational result | Transparent boundary |
|---|---|---|---|
| Division briefing cycle | Implemented baseline | Create a division-scoped recurring briefing using the existing governed Portfolio Review record | Enterprise calendar and meeting-service integration remain future work |
| Standard briefing structure | Implemented | Generates 15 consistent leadership sections for division comparison and review | Template authoring and approval administration remain roadmap |
| Source-backed division summary | Implemented | Aggregates standard-scope projects, demands, milestones, RAID, dependencies, resources, financials, benefits, status reports, and prior actions | Restricted, Sensitive, and Limited Distribution project/demand records are excluded and require a separate approved forum |
| Section preparation and readiness | Implemented | Assign owners, write narrative, track readiness, submit, approve, or return for changes | Does not silently correct underlying source data |
| Briefing snapshot | Implemented | Freezes the approved evidence and section narrative shown to leadership; section editing is locked after approval | Not a cryptographic signature or external records archive |
| Presentation mode | Implemented | Brief directly from the application with large-format section navigation and record drill-downs | Formal room-system integration and offline mode are absent |
| Review questions and responses | Implemented | Assign, answer, and close questions with due dates and audit evidence | Email/digest delivery requires future notification adapters |
| Governed change requests | Implemented baseline | Record current/proposed values, owner, rationale, due date, and disposition | Application does not automatically mutate arbitrary source fields |
| Review notes and parking lot | Implemented | Capture time-stamped discussion, observations, clarification, and parking-lot items | Formal transcript or recording integration is absent |
| In-review actions and decisions | Implemented | Reuses authoritative Action and Decision records rather than meeting-only lists | Complex approval chains remain policy-dependent |
| My Work follow-up | Implemented | Assigned briefing questions and change requests appear in the personal queue | Cross-system work assignment remains integration-dependent |
| Briefing closeout | Implemented | Requires unresolved follow-up acknowledgement before completion | External signatures and immutable archive remain planned |

## Platform release status

- Application version: 0.7.5.
- Migration head: `0007_division_experience_v075`.
- v0.6.1 role guidance, display preferences, and process orientation remain available.
- v0.5.0 portfolio governance, scenarios, integrations, data quality, report packs, resource requests, and financial evidence remain available.

---

# Feature Inventory — v0.6.1

## Role guidance and accessible workflow additions

- role-based focus strip and recommended navigation markers
- contextual process guides for all major menu workspaces
- Standard, Large, and Extra large browser-local text preferences
- Comfortable and Compact browser-local spacing preferences
- clearer input zones and required-field cues for substantial forms
- redesigned My Work personal workbench
- scalable small text, stronger focus indicators, and skip navigation

Transparent boundaries: preferences are not yet server-side; a formal WCAG 2.2 AA evaluation remains required; Kanban keyboard reordering and configurable workflow/form design remain incomplete.


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
- 313 packaged RTM records with filters, detail profiles, reverse links, design/module/test/release evidence
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


## v0.7.9 — Adoption, Focus & Workflow Simplification

| Feature | Description | Primary roles |
| ------- | ----------- | ------------- |
| Simplified navigation | Nine primary destinations; More workspaces + Administration & Assurance collapsible groups with persisted state; contextual shortcut strip | All |
| My Work Action Center | Unified prioritized queue (Critical now, Awaiting me, Due soon, Needs update, Watching, Recently completed) with per-item rationale and one primary action | Contributor, PM, PMO |
| Quick actions | Inline task percent/complete/blocker and action close-out; owner/PM permission, CSRF, full audit | Contributor, PM |
| Decision-first overview | Decisions Required and Significant Changes lead the dashboard; Investment Flow relocated to Investment analysis | Senior leader, Portfolio manager |
| Explainable health rollup | "Why? · View calculation" showing formula, counts, health precedence per project, and data freshness | Senior leader, PMO |
| Focused Travel workspaces | Overview / Requests / Trip Reports / Reconciliation / Engagement Outcomes with 25-row server-side pagination | PMO, Data steward, Division managers |
| Adaptive guidance & onboarding | Compact role-focus for returning users, collapsed page guides, role-specific Getting started checklist with restart | All |
| Help & glossary drawer | Searchable definitions (RAID, ROM, RTM, statuses, ROI, reconciliation, determination, stage gate, confidence) with owner and authoritative source | All |
| Adoption telemetry hooks | Local, privacy-conscious UX event ring buffer (`window.jsj6Telemetry`) ready for approved analytics tooling | Administrator |
| Release-version single source | `VERSION` file drives app metadata, UI, asset strings, and export schemas | Administrator |
