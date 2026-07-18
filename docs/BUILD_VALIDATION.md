# v0.6.0 Build Validation

## Automated test suite

Command:

```bash
pytest --cov=app --cov-report=term-missing -q
```

Result:

- 60 tests passed
- existing v0.5.0 coverage baseline remains 83%
- no test failures
- warnings were framework deprecation notices from the current Jinja/Starlette test stack

Coverage includes demand-to-project, scoring, permissions, audit, import, task, file, board, WBS, schedule, blueprint, status-report, search, and portfolio-overview behavior plus v0.5.0 and v0.6.0 capabilities:

- administration creates and updates users
- delegation registry creation and audit evidence
- ProjectOS dry-run canonical payload and no-remote-write behavior
- field-ownership and integration registry access
- portfolio-review decision creates linked Decision and Action records
- resource-request submit and decision workflow
- financial transaction creation
- non-destructive scenario calculation, approval, and governed apply
- data-quality scanning, issue update, and job history
- report-pack generation and approval
- division and restricted-record access boundaries

## Migration validation

### Clean database

- Alembic upgraded from base through `0005_portfolio_governance_v050`.
- Seed completed successfully.
- Seed totals included 25 users, 20 demands, 17 projects, 80 tasks, 35 milestones, 307 RTM rows, one portfolio review, one scenario, three integration connections, one resource request, one financial transaction, one report pack, and job evidence.

### In-place v0.4.0 upgrade

An actual v0.4.0 database was migrated and reseeded with the v0.5.0 source.

Preserved after upgrade:

- 25 users
- 20 demands
- 17 projects
- 80 tasks
- 307 RTM records

New v0.5.0 reference data was added without replacing existing project/demand/task records.

## Template and HTTP validation

- 43 Jinja templates compiled using the application environment and registered filters after removal of the legacy template.
- Authenticated smoke requests returned HTTP 200 for:
  - `/dashboard`
  - `/portfolio-reviews`
  - `/scenarios`
  - `/integrations`
  - `/resources`
  - `/financials`
  - `/data-quality`
  - `/operations`
  - `/administration`

## Static validation

- Python source compilation completed.
- JavaScript syntax validation completed.
- CSP-incompatible inline click handlers and JavaScript pseudo-links were inspected.
- Docker Compose YAML was parsed structurally.

## Docker limitation

The artifact environment does not provide a usable Docker daemon, so the full PostgreSQL, web, and Mailpit Compose stack could not be started here. The target host must execute:

```bash
docker compose up -d --build
docker compose ps
curl -fsS http://localhost:8080/health/ready
```

Container-health, reverse-proxy, browser, backup/restore, and persistence-after-restart results should be retained as deployment acceptance evidence.

## Release-package checks

Before publication the release archive is cleaned of local databases, uploaded test files, virtual environments, coverage residue, test caches, and compiled bytecode. ZIP integrity and SHA-256 verification are performed after packaging.
