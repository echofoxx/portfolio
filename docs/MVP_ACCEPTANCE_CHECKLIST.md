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
- [x] detailed task drawer persists notes, comments/mentions, checklist, relationships, files, evidence, and audit history.
- [x] search covers major scoped record types and no visible `K` artifact remains.
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
- [x] 37 tests passed with 85% application-code coverage in the release workspace.
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

## v0.3.1 hotfix acceptance

- [ ] Selecting a task from Kanban opens the detailed right-side workspace.
- [ ] Selecting a task from WBS opens the detailed right-side workspace.
- [ ] Opening the task link in a new tab displays the full authoritative task page.
- [ ] With JavaScript disabled or unavailable, the task link still reaches the full task page.
- [ ] Generated pages reference versioned v0.3.1 CSS and JavaScript assets.
- [ ] An eligible requester can edit a Submitted demand and save a required change summary.
- [ ] The demand version increments and the revision and audit records identify who changed what and when.
- [ ] A Clarification Required demand can be corrected and resubmitted.
- [ ] A stale form version cannot overwrite a newer demand revision.
- [ ] A requester cannot directly edit the demand after Assessment begins.


## v0.4.0 execution and deployment acceptance

- [x] Configurable board columns persist and enforce WIP server-side.
- [x] WBS numbering, baseline actions, cycle rejection, Gantt layout, and basic critical path are automated-test covered.
- [x] Task file versions, previews, download evidence, soft deletion, and restoration are automated-test covered.
- [x] Project blueprints create projects with immutable template provenance.
- [x] Status reports support draft/update/submit/return/resubmit/approve and governed reporting roll-up.
- [x] Exact-hop proxy client resolution and rate-limit headers are automated-test covered.
- [x] Clean migration and real v0.3.1 upgrade preserve 17 projects, 80 tasks, and 20 demands.
- [x] 50 automated tests pass with 83% application-code coverage in the artifact environment.
- [ ] Docker Compose containers confirmed healthy on the target Docker Desktop/host.
- [ ] Actual Synology/Nginx/Traefik/tunnel route verified with the configured hop count and independent client buckets.
- [ ] Authorized DDC5I users complete organization-level UAT and sign acceptance evidence.

## v0.5.0 governance and integration acceptance

- [x] Local administrator can create/update a user with roles, division scope, active state, and sensitive-access flag.
- [x] Acting-role delegation can be registered with roles, scope, dates, reason, and audit evidence.
- [x] Portfolio review can be created, populated with an agenda/recommendation item, and completed.
- [x] Review-item decision creates linked Decision and Action records.
- [x] Integration connection and field-ownership records are visible to authorized roles.
- [x] ProjectOS dry run creates a canonical project/task/milestone payload and records no remote write.
- [x] Resource request can be submitted and approved/declined.
- [x] Financial transaction evidence can be added to an accessible financial record.
- [x] Scenario changes do not alter live records before explicit approved apply.
- [x] Scenario apply records before/after audit evidence.
- [x] Data-quality scan creates/refreshes issues and persistent job evidence.
- [x] Data-quality issues can be assigned, dispositioned, and resolved.
- [x] Report pack can be generated from source records and approved.
- [x] Search includes v0.5.0 governance records and retains access filtering.
- [x] Clean migration and v0.4.0 upgrade migration pass without loss of core record counts.
- [x] 57 automated tests pass with 83% coverage.
- [ ] Full Docker Compose startup and health validated on target Docker Desktop/NAS host.
- [ ] Live ProjectOS connector authenticated and reconciled in an approved test environment.
- [ ] OIDC/CAC/PIV identity and delegated-role enforcement approved and validated.
- [ ] Durable worker/scheduler, signed report packages, and enterprise document/notification adapters validated.
