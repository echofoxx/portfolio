# Administrator Guide

## Responsibilities

The platform administrator owns local deployment configuration, migrations, backups, health monitoring, demonstration-user lifecycle, release installation, and coordination of security and integration decisions. The administrator does not become the business owner of portfolio data merely by holding technical privileges.

## Administration page

Sign in as `admin` and open **Administration** to inspect:

- user identities, roles, division scope, and sensitive-access flag;
- record counts;
- configured integration boundaries and unresolved authoritative-field decisions;
- local demonstration-authentication warning.

User create/edit screens are intentionally omitted from this MVP to avoid presenting a partial identity-management workflow as production-ready. Seed users are defined in `app/seed.py`. Future enterprise identity should provision stable subject identifiers and role/group claims through the authentication adapter.

## Configuration

Primary local configuration is through `.env`. Never commit `.env`. The checked-in `.env.example` contains placeholders only.

Required production changes include:

- replace `SECRET_KEY` and database password;
- set `ENVIRONMENT=production` for secure cookie behavior;
- disable demonstration authentication when an approved identity adapter exists;
- publish behind an approved TLS reverse proxy;
- restrict Mailpit and database networks;
- move secrets to an approved secrets manager;
- configure centralized logs, monitoring, backup retention, and alerting.

## Migrations

Migrations live in `migrations/versions`. Startup applies them automatically. Before a production migration:

1. back up the database;
2. test upgrade against a restored copy;
3. review generated DDL;
4. document rollback or forward-fix steps;
5. schedule downtime when required;
6. validate record counts and key workflows after upgrade.

## Seed behavior

`python -m app.seed` exits when the user table is populated. It is safe for ordinary container restarts and does not reseed or overwrite existing data. Use volume reset only for a deliberate demonstration reset.

## RTM administration

The RTM is seeded from `app/data/requirements.json`. In the UI, authorized administrators, PMO users, and data stewards can update:

- implementation status;
- design reference;
- module/API reference;
- test case;
- UAT result;
- release;
- acceptance notes;
- decision/comments.

Material RTM changes are audited. Do not bulk-mark requirements Implemented without evidence.

## Import administration

Only XLSX demand imports are committed in this MVP. Uploads are size-limited and parsed locally. Preview results must be reviewed before commit. Valid and warning rows may be committed; error rows remain excluded. Every committed row carries source-system and batch-row lineage.

## Backup and recovery

Use `scripts/backup.sh` and `scripts/restore.sh`. Test restore procedures on a separate environment. PostgreSQL backup does not include the file-storage volume; back up that volume separately when operational attachments are enabled.

## Health and logs

- `/health/live` confirms process liveness.
- `/health/ready` performs a database query.
- `docker compose ps` shows container health.
- `docker compose logs -f web db` shows application/startup/database logs.

The current logger is container stdout/stderr. Production requires structured log aggregation, correlation identifiers, retention, access controls, and alerting.

## Data-quality operations

Review stale project indicators, unaligned work, missing status, import errors, over-allocation, underfunding, low milestone confidence, open critical RAID, and RTM gaps. Assign the owning division or data steward rather than silently correcting authoritative business facts.

## Integration governance

Before registering a live adapter, populate field-ownership rules. A connector must not independently overwrite a field already owned by another source. Define retry and reconciliation thresholds, operator ownership, dead-letter handling, idempotency, source lineage, and audit requirements.

## Production readiness gate

The MVP must not be represented as operationally authorized until the organization completes identity integration, threat modeling, vulnerability management, dependency scanning, secrets management, backup/recovery exercises, records/privacy review, accessibility review, performance testing, high-availability design, monitoring, incident response, and RMF/authorization processes.
