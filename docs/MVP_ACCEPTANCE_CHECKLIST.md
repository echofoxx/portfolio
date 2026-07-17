# MVP Acceptance Checklist

## Build and startup

- [ ] `docker compose up -d --build` completes on the target Docker Desktop host.
- [ ] `db`, `web`, and `mailpit` become healthy.
- [ ] `/health/ready` returns database connected.
- [x] migration and idempotent seed logic are included.
- [x] no runtime CDN dependency is present.

## First-build experience

- [x] documented demonstration accounts exist.
- [x] executive dashboard is populated.
- [x] enterprise and six division views exist.
- [x] demand can be saved as draft and submitted.
- [x] triage and clarification are functional.
- [x] assessment, scoring and comparison are functional.
- [x] recommendation and decision gates are functional.
- [x] decision rationale, evidence, conditions and tradeoff are captured.
- [x] approved demand converts to a project without rekeying.
- [x] project tasks, Kanban, milestones, RAID, dependencies and status are usable.
- [x] status changes roll up to dashboards.
- [x] executive metrics drill to source records.
- [x] filters, search, saved views and accessible CSV exports are available.
- [x] audit history records material changes.
- [x] demand Excel preview produces row-level results and correction output.
- [x] all visible actions are intended to be functional; unusable capabilities are omitted/documented.

## Security and access

- [x] passwords are hashed.
- [x] CSRF, session, security headers and login throttle are implemented.
- [x] server-side role checks are implemented.
- [x] division-scoped user cannot access another division’s record.
- [x] restricted record check is implemented.
- [x] auditor can view evidence but cannot alter business data.
- [x] sensitive rate notes are not displayed in broad dashboards.
- [ ] enterprise identity, CAC/PIV and production authorization are completed before operational use.

## Demonstration data

- [x] 6 division portfolios.
- [x] 12 core functions.
- [x] 20 demands.
- [x] 12 active, 3 completed and 2 archived/canceled projects.
- [x] 35 milestones.
- [x] 80 tasks.
- [x] 20 risks/issues/assumptions/roadblocks.
- [x] 15 dependencies.
- [x] 10 decisions.
- [x] 12 actions.
- [x] 25 users.
- [x] resources, skills, capacity, financials and benefits.
- [x] stale/incomplete data and restricted/cross-division examples.

## Traceability and tests

- [x] all 307 RTM rows are represented.
- [x] implementation status is transparent and conservative.
- [x] tests reference the primary workflow and security scenarios.
- [x] 25 tests passed with 88% application-code coverage in the release workspace.
- [ ] target-host Docker test passes.
- [ ] authorized DDC5I UAT is executed and signed.
- [ ] accessibility and security assessments are completed.

## Documentation and deliverables

- [x] source code, Dockerfile, Compose, environment example.
- [x] schema, migration and seed.
- [x] OpenAPI documentation.
- [x] architecture, data-model and integration diagrams.
- [x] role and permission matrix.
- [x] traceability report.
- [x] automated tests.
- [x] versioned Excel templates.
- [x] backup/restore instructions.
- [x] README, installation, admin and role guides.
- [x] demonstration, troubleshooting and security guides.
- [x] screenshots.
- [x] feature inventory, limitations, roadmap and release notes.

## Acceptance authority

| Review | Name / organization | Date | Result / comments |
|---|---|---|---|
| Product owner |  |  |  |
| PMO / portfolio owner |  |  |  |
| Security / privacy |  |  |  |
| Data steward |  |  |  |
| Platform operations |  |  |  |
| UAT lead |  |  |  |
