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

The MVP includes in-app notifications and a Mailpit container boundary. Not every notification currently emits SMTP mail. Mailpit demonstrates the local delivery destination for the planned sender job; in-app notification records are authoritative in 0.4.0.

## Browser layout problem

Use a current Edge or Chrome build, hard-refresh, and verify that `/static/app.css` and `/static/app.js` return 200. The application does not require an external CDN. Clear only site cache, not the database.

## Backup or restore fails

Verify the backup file exists, gzip can read it, the database container is healthy, and environment user/database names match. A restore recreates the database and is destructive. Test on an isolated copy first.

## Tests fail outside Docker

The test suite configures SQLite before importing the application. Install dependencies from `requirements.txt` and run from the repository root. Docker remains the supported deployment database; local SQLite is not the production datastore.


## Search shows a stray K or does not submit

Confirm the application reports v0.4.0 and the generated page references `/static/app.js?v=0.4.0`. Rebuild the web image if an older unversioned bundle is served. The search form contains a submit button and no visible keyboard-label element. Command/Ctrl+K still focuses search.

## Task drawer does not open

Task controls in v0.4.0 remain normal links with progressive drawer enhancement. If the drawer cannot open, the browser should navigate to the full task page. Confirm the link points to `/projects/<project-id>/tasks/<task-id>`, then inspect `docker compose logs -f web` for a failed `/panel` request. A 404 means the task is outside the current user’s project, division, or sensitivity scope.

## Task file upload is rejected

- Check the extension against PDF, DOCX, XLSX, PPTX, CSV, TXT, MD, JSON, PNG, JPG, and JPEG.
- Check `MAX_UPLOAD_MB`.
- Do not rename a different binary to an allowed extension; PDF/image/Office signatures are checked.
- Confirm the storage volume is writable and has free space.
- Review the redirected validation message and web logs.

## Reverse proxy or rate-limit identity problems

v0.4.0 uses `TRUST_PROXY_HOPS`, not Express `app.set('trust proxy')`.

- Direct access: `TRUST_PROXY_HOPS=0`
- One Synology/Nginx/Traefik/tunnel proxy: `TRUST_PROXY_HOPS=1`
- Two controlled proxies: `TRUST_PROXY_HOPS=2`

Rebuild after changing `.env`. Inspect response headers with:

```bash
curl -I https://your-host/health/ready
```

Confirm `X-Resolved-Client-IP-Source` is `forwarded` when proxied. Do not use more hops than the actual controlled path.

## Task drawer does not open

The Details link is a full-page fallback. Open it in a new tab or reload the page. Confirm `/static/app.js?v=0.4.0` loads with HTTP 200 and clear any proxy/browser cache that ignores query-string versioning.

## A Kanban move is rejected

The target column may have reached its WIP limit or may have been archived. Open Board Configuration and review the current count, limit, and criteria.

## A status report cannot be edited

Only Draft and Returned reports are editable. Submitted reports must be returned by an authorized reviewer. Approved reports remain locked as reporting baselines.

## v0.5.0 troubleshooting

### ProjectOS sync says dry run or no remote write

This is expected. The seeded ProjectOS connection is `Mock`; v0.5.0 validates and stores the canonical payload but does not contact an external endpoint. Do not mark it External until the target API, credentials, ownership rules, retry/reconciliation, and network access are approved.

### Integration health says External Test Required

The base URL is structurally valid, but the application cannot prove target authentication/connectivity in the local reference environment. Check enabled state, mode, base URL, secret-manager integration, reverse proxy/firewall, and target API availability.

### Scenario cannot be applied

Calculate the scenario first, then approve it with an authorized portfolio/approval role. Only status `Approved` can be applied. Approved or applied scenarios are locked against new proposed changes.

### Scenario result appears stale

v0.5.0 does not automatically invalidate results when source data changes. Recalculate before approval/apply whenever project, capacity, or financial baselines have changed.

### Delegation does not change access

This is a known v0.5.0 boundary. The application records and audits delegation terms but does not yet inject delegated roles into every authorization decision. Assign approved temporary local roles directly only under administrator/security governance, or wait for v0.6.0 enforcement.

### Data-quality scan returns the same issue

The scanner refreshes existing open findings rather than duplicating them. Correct the authoritative source or document an approved disposition, then update the issue status. A future rule engine will support rule versions and automatic revalidation.

### Report pack is not emailed or scheduled

Report generation is currently an operator action and job record. Mail/SharePoint distribution and a durable scheduler/worker are planned for v0.6.0.
