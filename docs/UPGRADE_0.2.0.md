# Upgrade to v0.2.0

## Supported path

v0.2.0 is an in-place application upgrade from v0.1.0. It does not introduce a destructive database migration. Existing PostgreSQL data and Docker volumes remain authoritative.

1. Back up the database and `storage` volume.
2. Stop the v0.1.0 stack: `docker compose down`.
3. Replace the source tree with v0.2.0 while retaining `.env` and named volumes.
4. Run `docker compose up -d --build`.
5. Confirm `docker compose ps` reports healthy services.
6. Sign in and validate `/dashboard`, `/war-room`, `/projects`, `/demands`, and `/requirements`.

## User-visible changes

- Modern Enterprise is the default light interface.
- Mission Command styling is activated with dark mode.
- Executive War Room is available to authorized leadership and portfolio roles.
- Project and demand pages include requirement traceability cards.
- Tasks, milestones, RAID records, dependencies, decisions, and actions support direct detail views.
- Requirement IDs open evidence profiles with reverse links to implementation surfaces.

## Rollback

Stop the stack, restore the prior source image/tag, and restart using the unchanged v0.1.0 database volume. Because no destructive schema migration is included, application rollback is straightforward. Always retain the pre-upgrade backup until operational verification is complete.
