# Feature Inventory

## Implemented and usable

### Platform

- Dockerfile and Docker Compose
- PostgreSQL 16 and named volume
- Alembic migrations and idempotent seed
- application/database health endpoints
- local Mailpit container
- local file-storage, integration, and job interfaces
- authenticated OpenAPI document

### Identity and access

- local demonstration login
- PBKDF2 password hashing
- signed session cookie and CSRF
- role checks
- enterprise and division scope
- restricted-record access
- auditor read-only behavior
- login attempt throttle
- audit login/logout

### Strategy and organization

- DDC5I Enterprise plus JAD, DSD, AID, CID, JFID, C3OD2
- six missions
- twelve recurring core functions
- division and enterprise roll-up
- mission-to-demand/project/function counts
- unaligned demand visibility

### Demand, assessment, and decisions

- guided intake with draft/submit
- core readiness validation
- lifecycle stages and transition roles
- current owner, next action, pending information, target decision date, disposition
- revisions and comments
- 100-point weighted scoring
- multiple assessors, confidence, variance, adjudication
- comparison page
- stage gates and decision record
- capacity-tradeoff validation
- decision conditions converted to actions
- approved demand converted to linked project without rekeying

### Portfolio and projects

- six division portfolios
- project inventory and filters
- project overview/status
- owner/calculated/override health fields
- tasks with sequence, indent, baseline/current dates, owner, effort, progress, checklist, notes, acceptance evidence
- Kanban with drag/move API
- milestones with baseline/current date, confidence and critical flag
- RAID with type, severity, likelihood, consequence, exposure, mitigation, due date and escalation
- cross-project dependencies
- decisions, actions, financials, benefits
- source drill-down

### Resources, finance, and value

- role/skill/period capacity
- allocation, actual effort and utilization
- over-allocation and core-coverage warning
- budget, actual, forecast and variance
- minimum viable and full requirement
- funding status and category
- benefit register with target, realized, unit, status, owner and review

### Dashboards, reports, and collaboration

- exception-focused executive dashboard
- six division dashboards
- demand pipeline
- leadership exceptions
- milestones and dependencies
- capacity, financial and benefit summaries
- stale-data indicators
- source-grounded narrative
- metric metadata
- notification center
- My Work
- global search
- saved views
- CSV export
- browser print/PDF-ready report view

### Import, traceability, and audit

- versioned workbook with eight template sheets
- demand import preview
- create/update/duplicate/warning/error/permission outcomes
- commit valid rows
- correction workbook
- source batch/row lineage
- 307 RTM rows
- RTM filters and updates
- material before/after audit events
- data-quality examples

## Partially implemented

- configurable organization hierarchy: data model supports parent relationships; full admin editor is absent
- conditional intake: fields and validation exist; form-schema designer is absent
- attachments: secure storage adapter exists; full record UI/records lifecycle is absent
- scoring configuration: criteria are visible and isolated in a service; database administration is absent
- portfolio taxonomy/baselines/roadmaps: core portfolio records exist; advanced management is absent
- WBS/schedule: hierarchy and baseline fields exist; critical-path engine and rich editor are absent
- relationship graph: dependencies are tabular; interactive accessible graph is roadmap
- comments/mentions: rationale and history exist; threaded discussion/mentions are roadmap
- notifications: in-app works; digest and SMTP/Graph delivery job is roadmap
- narrative: source-grounded text works; editable/versioned narrative approval is roadmap
- data quality: stale/unaligned/capacity/funding indicators exist; configurable rule engine is roadmap
- delegation: user model fields exist; workflow/UI is roadmap

## Planned, integration-dependent, governance-dependent, or deferred

See the in-app RTM, `DDC5I_RTM_MVP_Status.csv`, Known Limitations, and Roadmap. Major areas include enterprise identity, full user lifecycle, detailed workforce and finance, records/document management, ProjectOS/ServiceNow/Microsoft/Advana/WDP integrations, durable background jobs, advanced reports, scenarios/optimization, and responsible AI.
