# Release Notes

## 0.1.0 — Usable MVP reference implementation

### Added

- Docker Compose topology with PostgreSQL, web service, Mailpit, persistent volumes, health checks, migration and seed startup.
- local demonstration authentication, PBKDF2 hashing, session/CSRF, RBAC, division scope, sensitivity checks, audit, security headers and login throttle.
- DDC5I enterprise plus JAD, DSD, AID, CID, JFID and C3OD2 hierarchy.
- mission and recurring core-function catalog.
- governed demand intake, lifecycle, triage, clarification, revision history, stage gates and ownership status.
- weighted assessment, confidence, multiple assessor variance and comparison.
- leadership decision records, capacity tradeoffs, conditions and follow-up actions.
- no-rekey approved-demand-to-project conversion.
- portfolio/project inventory, task/WBS fields, Kanban, milestones, RAID, dependencies, status, finance and benefits.
- executive and division dashboards with drill-down, stale data, metric governance and source-grounded narrative.
- role/skill capacity and basic financial/benefit decision support.
- in-app notifications, My Work, global search, saved views, CSV exports and browser print.
- XLSX demand preview/commit/correction and an eight-sheet versioned template workbook.
- all 307 RTM records with conservative implementation classification.
- comprehensive documentation, diagrams and ten screenshots.
- 25 automated tests covering the primary acceptance paths, integration interfaces, secure workbook handling, and service adapters; 88% application-code coverage.

### Fixed during validation

- corrected Jinja resource-utilization threshold expression.
- ensured the demonstration seed contains exactly ten decision records.
- improved navigation semantics and global-search accessible naming.

### Known limitations

See `KNOWN_LIMITATIONS.md`. Most importantly: no enterprise identity or live external integration, no production authorization, Demand-only committed XLSX import, basic rather than detailed workforce/financial/schedule modules, and Docker launch must be validated on the target host.

### Recommended next release

0.2.0 should expand schedule/WBS depth, templates/blueprints, advanced RAID and dependency graph, recurring report packs, meeting support, document/records controls, database-configurable scoring/governance, and a governed ProjectOS connector pilot.
