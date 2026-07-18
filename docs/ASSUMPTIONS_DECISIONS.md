# Assumptions and Open Decisions

## Implementation assumptions

1. DDC5I may use a vendor-neutral reference application before selecting or configuring an enterprise platform.
2. The first build must remain useful with no ServiceNow, ProjectOS, Microsoft 365, Advana/WDP, financial, workforce, or enterprise identity connection.
3. FastAPI is an acceptable comparable stack because it meets deployment, security, persistence, OpenAPI, maintainability, accessibility, testing, and offline-runtime objectives.
4. PostgreSQL is the authoritative MVP store; SQLite is used only for local automated-test execution in the build workspace.
5. All demonstration data is synthetic and not an operational statement.
6. The 307 RTM rows are imported exactly as traceability records and then assigned a separate implementation status; source priority/phase/fit are preserved.
7. Role-based capacity is sufficient for MVP decisions; person-level calendars and rates are not.
8. Basic financial values are decision-support estimates; commitments, obligations, expenditures, and rates remain external-authority data.
9. Browser printing is the MVP PDF-ready mechanism; server-generated signed PDF packs are later work.
10. Demand XLSX import is the first fully committed template; other workbook sheets are versioned contracts until their vertical slices are built.
11. Local Mailpit is optional evidence of notification delivery and does not represent Outlook integration.
12. A modular monolith provides the lowest-risk path to first-use while preserving adapter and service boundaries.

## Open governance decisions

| Decision | Why it matters | Recommended owner | Blocking capability |
|---|---|---|---|
| System of record by field when ServiceNow/ProjectOS are connected | prevents dual writers and silent conflicts | Enterprise Portfolio Owner + CIO/data governance | live bidirectional integration |
| Authoritative demand-intake platform | avoids multiple funnels | DDC5I leadership / PMO | ServiceNow SPM design |
| Project execution authority and summary-health derivation | determines task/schedule/status ownership | PMO + ProjectOS owner | ProjectOS connector |
| Approval authority thresholds and delegation | controls legal/mission accountability | DDC5I leadership | delegated approvals |
| Capacity-overrun tradeoff authority | determines who can stop/delay work | DDC5I leadership | portfolio optimization |
| Sensitivity taxonomy and field-level protections | affects access, export, email, and analytics | Security/privacy/data governance | production authorization |
| Records schedule and document repository | determines retention and disposition | Records manager | document integration |
| Financial data granularity and rate restrictions | protects workforce and rate information | Financial manager + security | detailed financial module |
| Workforce data authority and skill governance | affects people/position/skill decisions | Resource manager / HR authority | detailed resource module |
| Health calculation, thresholds, and override authority | ensures consistent executive reporting | Portfolio governance forum | configurable health engine |
| Reporting period and stale-data cadence | controls alerts and narrative | PMO / data steward | scheduled checks |
| UAT and release acceptance authority | establishes Definition of Done evidence | Product owner + security + operations | operational release |
| AI use cases, data boundaries, evaluation, and human review | prevents premature or ungoverned automation | Responsible AI governance | Phase 5 AI |

## Open technical decisions

- approved enterprise hosting platform and network zone;
- TLS/reverse proxy and domain;
- secrets manager;
- centralized logging/SIEM and event schema;
- object storage and malware scanning;
- durable job queue and scheduler;
- external API versioning and gateway;
- analytics data-product format and refresh contract;
- high availability, backup retention, recovery objectives;
- pagination and scale targets;
- browser and accessibility validation tooling;
- approved dependency registry and software-composition process.

## v0.5.0 assumptions and unresolved decisions

1. ProjectOS remains Mock/Dry Run until a target test endpoint, service identity, field mapping, idempotency key, retry policy, conflict authority, and reconciliation owner are approved.
2. Local user administration is for the reference deployment; enterprise identity remains authoritative in production.
3. Delegation records do not grant access until delegated-role enforcement and separation-of-duties policy are approved.
4. Resource requests represent role/skill/hour demand and do not create official personnel assignments.
5. Financial transactions are portfolio planning/evidence records, not official accounting postings or funds-control actions.
6. Scenario application is permitted only for the supported application fields and does not replace required external financial/workforce/leadership approvals.
7. Data-quality findings are owned by business/data stewards; the scanner does not silently correct authoritative source records.
8. Report packs are snapshots, not signed records. The approved repository, retention schedule, distribution policy, and electronic signature method remain decisions.
9. Job runs provide persisted evidence; an approved queue/worker/scheduler technology remains unresolved.
10. OIDC is the recommended first enterprise identity adapter, but the approved broker and CAC/PIV path remain organizational decisions.
