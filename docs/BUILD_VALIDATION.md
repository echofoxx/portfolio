# Build Validation

Release: `0.1.0-mvp`

Validated in the artifact workspace:

- 29 Jinja templates compiled using the application filter registry.
- Python source and migration modules compiled successfully.
- A clean Alembic migration completed against a new database.
- The seed process completed twice without duplicate failure.
- Seed reconciliation confirmed 25 users, 7 organizations, 6 missions, 12 core functions, 20 demands, 17 projects, 80 tasks, 35 milestones, 20 RAID records, 15 dependencies, 10 decisions, 12 actions, and 307 RTM records.
- Docker Compose YAML parsed with the expected `db`, `web`, and `mailpit` services and persistent volumes.
- 25 automated tests passed with 88% application-code coverage.
- Versioned Excel templates were parsed and validated with row-level success, warning, duplicate, and error outcomes.
- Ten authenticated application screenshots were generated from seeded routes.

The artifact-build environment did not expose a Docker daemon. The complete Compose stack must therefore receive final target-host validation with `docker compose up -d --build`, container health checks, and the acceptance test command documented in the README. This is a packaging limitation, not a claim of production authorization.
