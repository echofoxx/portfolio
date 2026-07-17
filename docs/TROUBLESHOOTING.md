# Troubleshooting Guide

## Containers do not start

```bash
docker compose ps
docker compose logs --tail=200 db web mailpit
```

Common causes:

- Docker Desktop is not running.
- `.env` is missing or contains invalid characters.
- ports 8080, 8025, or 1025 are already in use.
- image build cannot reach the approved package/container registry.
- insufficient disk or memory.

Change host ports in `.env`, then rerun `docker compose up -d --build`.

## Web container repeatedly restarts

Inspect the first exception in `docker compose logs web`. Typical categories:

- database password or database name does not match;
- migration failed;
- a modified seed file violates a uniqueness constraint;
- file permissions prevent storage-directory creation;
- a dependency failed to install during image build.

Do not repeatedly delete volumes before preserving logs and a backup.

## Database is unhealthy

```bash
docker compose logs db
docker compose exec db pg_isready -U ddc5i -d ddc5i_portfolio
```

Ensure the environment values used by `web` and `db` match. If a password was changed after the volume was initialized, the existing PostgreSQL role keeps the prior value; restore from backup or deliberately reset the local volume.

## Login fails

Use one of the documented usernames and `Demo123!`. Usernames are case-insensitive. After ten failed attempts from one IP in five minutes, wait for the local limiter window or restart the web container in a demonstration environment.

If the database was restored from a non-seeded environment, verify that users exist.

## Page redirects to login

The signed session may have expired, the secret key may have changed, or the cookie may have been cleared. Sign in again. In production behind TLS, confirm `ENVIRONMENT=production` and correct reverse-proxy headers/cookie behavior.

## Access denied or record not found

- 403 indicates the role cannot perform the action or CSRF is invalid.
- 404 for a known UUID may indicate division or sensitivity scope denial.
- auditors cannot change business records.
- restricted records require approved sensitive access.

Test with `admin` only to distinguish configuration from data problems; do not use admin as the permanent workaround.

## Import rejected

Confirm:

- file is `.xlsx` and under the configured size limit;
- the first sheet contains all required Demand headers;
- division and mission values match reference codes;
- ROM cost is numeric and non-negative;
- IDs are not duplicated within the upload;
- the user has organization and sensitivity permission.

Use the provided demo workbook and download the correction workbook after preview.

## Dashboard totals seem wrong

Filters and RBAC apply before aggregation. A division user will not see other divisions or restricted records. Check:

- current signed-in role and division;
- project status is Active;
- owner/calculated/override health values;
- reporting date and stale threshold;
- source record and audit history;
- whether a seeded/test workflow changed data.

Reset only if this is a disposable demonstration environment.

## Data does not reset

The database is in a Docker named volume. `docker compose down` preserves it. Use the destructive reset:

```bash
docker compose down -v
docker compose up -d --build
```

## Mailpit is empty

The MVP includes in-app notifications and a Mailpit container boundary. Not every notification currently emits SMTP mail. Mailpit demonstrates the local delivery destination for the planned sender job; in-app notification records are authoritative in 0.1.0.

## Browser layout problem

Use a current Edge or Chrome build, hard-refresh, and verify that `/static/app.css` and `/static/app.js` return 200. The application does not require an external CDN. Clear only site cache, not the database.

## Backup or restore fails

Verify the backup file exists, gzip can read it, the database container is healthy, and environment user/database names match. A restore recreates the database and is destructive. Test on an isolated copy first.

## Tests fail outside Docker

The test suite configures SQLite before importing the application. Install dependencies from `requirements.txt` and run from the repository root. Docker remains the supported deployment database; local SQLite is not the production datastore.
