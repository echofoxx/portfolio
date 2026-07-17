# Known Limitations

## Deployment and authorization

- Docker Compose was not executed inside the artifact-build environment because no Docker daemon was exposed. Source, migrations, seed, local server, routes, tests, and health behavior were validated; the target Docker Desktop host must execute the Compose acceptance check.
- The application is not RMF-authorized, production-authorized, CAC-enabled, or PIV-enabled.
- Local demonstration accounts and synthetic data are not suitable for operational use.

## Functional depth

- Demand is the only workbook type with complete preview/commit behavior. Other sheets are versioned contracts.
- Attachments do not yet have a complete UI, malware scanning, records metadata, or repository lifecycle.
- The built-in WBS and schedule capability does not provide a critical-path engine, resource leveling, advanced recurrence, or full baseline/version management.
- Kanban supports card movement but not WIP limits, swimlanes, bulk operations, or full accessibility parity with keyboard reordering.
- Project closure checklist, formal status-report versions, lessons workflow, and acceptance-signature process require expansion.
- Portfolio roadmaps and baselines are represented at a basic level rather than a full interactive planning tool.
- Relationship dependencies are shown in tables; an interactive graph is planned.

## Resource, financial, and value data

- capacity is role/skill based and synthetic, not authoritative person-level availability.
- vacancies, contractors, leave calendars, position management, and skill proficiency are not implemented.
- financials are basic budget/actual/forecast demonstration values; commitments, obligations, expenditures, rates, EAC methods, and multi-year profiles are not authoritative.
- benefit attribution and ROI analysis are basic.

## Collaboration and reporting

- in-app notifications work; digest scheduling and outbound SMTP/Graph messages are not fully wired.
- comments are represented through rationale, notes, and revision history rather than a complete threaded mention/resolution system.
- PDF uses browser printing; no server-generated signed PDF package is present.
- narrative generation is deterministic and source-grounded but not yet an editable, approved report artifact.

## Administration

- no full UI for user creation, role assignment, delegation, organization editing, reference-data editing, or configuration promotion.
- scoring weights and many thresholds are service configuration rather than database-managed records.
- project membership and row/field policy management are not fully normalized.
- audit events are not tamper-evident and are not forwarded to a SIEM.

## Integrations

- no live ServiceNow SPM, ProjectOS, Microsoft Graph, SharePoint, Power BI, Advana/WDP, financial, workforce, Jira, Azure DevOps, records, or enterprise identity connection.
- adapter protocols and field-ownership registry are present, but durable events, retry queues, dead-letter handling, reconciliation UI, and service credentials are not.

## Nonfunctional evidence

- formal WCAG 2.2 AA/Section 508 expert certification has not been performed.
- representative performance/load testing and the three-second 95th-percentile target have not been demonstrated.
- 99.9% availability, high availability, recovery objectives, disaster recovery, and restore exercises have not been demonstrated.
- dependency, container, SAST, DAST, penetration, and formal threat-model evidence are not included.
- browser validation is focused on current Chromium rendering; target enterprise Edge/Chrome versions require acceptance testing.

## AI

No operational AI is included. This is intentional. Responsible AI requirements are deferred until data quality, lineage, access, metrics, evaluation, audit, and human-review controls are established.
