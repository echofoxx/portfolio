# Backup and Restore

## PostgreSQL backup

```bash
./scripts/backup.sh
```

The script executes `pg_dump` inside the database container, compresses the output, writes a timestamped file to `backups/`, and updates `backups/latest.sql.gz`.

## Restore

```bash
./scripts/restore.sh backups/ddc5i-YYYYMMDD-HHMMSS.sql.gz
```

The script stops the web service, recreates the database, restores the SQL stream, and starts the web service.

## Required production additions

- copy backups to an approved encrypted location;
- define retention and legal/records requirements;
- include Docker file-storage/object-storage content;
- protect backup credentials and access;
- verify checksums;
- test restore on an isolated environment at an approved cadence;
- record recovery time and recovery point results;
- test schema upgrade after restore;
- document partial/point-in-time recovery when enabled.

## Restore verification checklist

- containers become healthy;
- migrations show the expected revision;
- user, organization, demand, project, task, RTM, and audit counts reconcile;
- restricted records remain restricted;
- recent audit events and attachments are present;
- primary workflow and exports operate;
- no seed duplication occurred.

The scripts are appropriate for local MVP operations but are not a substitute for a production backup architecture or tested continuity plan.
