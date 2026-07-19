# Docker Desktop Installation Guide

## Supported local topology

Docker Compose starts three containers:

| Service | Container purpose | Host port | Persistent volume |
|---|---|---:|---|
| `web` | FastAPI application, migrations, seed, OpenAPI, health endpoints | `8080` | `ddc5i_storage` |
| `db` | PostgreSQL 16 canonical database | not published | `ddc5i_pgdata` |
| `mailpit` | local SMTP capture and browser mailbox | `1025`, `8025` | none required |

## Windows 11 with Docker Desktop

1. Install Docker Desktop and enable the WSL 2 backend.
2. Confirm Docker Desktop is running.
3. Extract the release to a local folder such as `C:\docker\ddc5i-portfolio`.
4. Open PowerShell in that folder.
5. Run:

```powershell
Copy-Item .env.example .env
notepad .env
```

Replace the placeholder database password and secret key. Then run:

```powershell
docker compose up -d --build
docker compose ps
Invoke-WebRequest http://localhost:8080/health/ready
```

Open `http://localhost:8080` in Edge or Chrome.

### Windows file-sharing note

The Compose file uses named Docker volumes, not host bind mounts, so no folder-sharing configuration is normally required. Backups are written to the local `backups` folder by the backup script.

## macOS with Docker Desktop

1. Install and start Docker Desktop.
2. Extract the release.
3. In Terminal:

```bash
cd /path/to/ddc5i-portfolio-mvp
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Place the generated secret in `.env`, choose a strong PostgreSQL password, and run:

```bash
docker compose up -d --build
docker compose ps
curl -fsS http://localhost:8080/health/ready
```

## Linux

Docker Engine 24+ and the Compose plugin are recommended:

```bash
cp .env.example .env
docker compose up -d --build
```

Ensure the current user can run Docker commands or use the approved local privilege process.

## First-start sequence

The `web` entrypoint performs these steps on every start:

1. Retry database connectivity for up to approximately two minutes.
2. Run `alembic upgrade head`.
3. Run the idempotent seed command. Existing user-created records are preserved while required v0.5.0 reference data and packaged RTM evidence are synchronized.
4. Start Uvicorn on `0.0.0.0:8080`.
5. Docker polls `/health/ready` until PostgreSQL and the web service are ready.

## Validate the deployment

```bash
docker compose ps
docker compose logs --tail=100 web db
curl -fsS http://localhost:8080/health/live
curl -fsS http://localhost:8080/health/ready
```

Expected services show `healthy`. Sign in as `admin / Demo123!` and confirm:

- the executive dashboard is populated;
- the division selector and navigation work;
- a demand detail page opens;
- a project board opens and a task detail drawer can save notes;
- a permitted task file can be uploaded and downloaded;
- global search returns a task by stable ID and shows no visible `K` artifact;
- Requirements RTM shows 313 packaged rows before filtering;
- Administration shows 25 users, 20 demands, and 17 projects.

## Ports

Change host ports in `.env` when conflicts exist:

```dotenv
APP_PORT=8088
MAILPIT_UI_PORT=8026
MAILPIT_SMTP_PORT=1026
```

Then use `http://localhost:8088`.

## Upgrade procedure

1. Back up the current database.
2. Review release notes and [`UPGRADE_0.5.0.md`](UPGRADE_0.5.0.md).
3. Pull or replace source files.
4. Rebuild:

```bash
docker compose up -d --build
```

5. Verify `alembic current`, health endpoints, logs, and primary workflows.
6. Keep the previous image/tag and backup until acceptance is complete.

## Uninstall

Preserve data:

```bash
docker compose down
```

Delete application data:

```bash
docker compose down -v
```

The second command is destructive and should be preceded by a backup.

## Offline operation

Runtime pages, styles, scripts, charts, database operations, and demonstration workflows have no CDN dependency. The initial image build requires access to the configured container registry and Python package index unless images and packages are pre-staged in an approved offline repository.

## v0.4.0 reverse-proxy configuration

Direct local access:

```env
PUBLIC_BASE_URL=http://localhost:8080
TRUST_PROXY_HOPS=0
```

One controlled reverse proxy:

```env
PUBLIC_BASE_URL=https://your-portfolio-host.example
TRUST_PROXY_HOPS=1
```

After changing `.env`:

```bash
docker compose up -d --build
docker compose logs -f web
```

Open Administration and verify the effective proxy and rate-limit settings. Refer to `docs/REVERSE_PROXY.md` for multi-proxy paths and security limitations.


## v0.4.0 environment settings

Set these values in `.env` before building:

```env
PUBLIC_BASE_URL=http://localhost:8080
TRUST_PROXY_HOPS=0
RATE_LIMIT_REQUESTS=300
RATE_LIMIT_WINDOW_SECONDS=900
```

Use `TRUST_PROXY_HOPS=1` only when exactly one controlled reverse proxy sits between the browser and the application. See `REVERSE_PROXY.md` for Synology, Nginx, Traefik, and tunnel patterns.

## v0.5.0 first-run verification

After containers become healthy, sign in as `admin` and verify:

1. **Administration** lists users, organizations, roles, and the seeded delegation/reference areas.
2. **Integrations** lists ProjectOS Mock plus disabled Microsoft 365 and SharePoint entries and field-ownership rules.
3. **Portfolio Reviews**, **Scenarios**, **Data Quality**, and **Operations** open without errors.
4. **Resources** includes resource requests and **Financials** includes transaction evidence.
5. The Requirements RTM contains 313 packaged rows.

Run the release regression suite:

```bash
docker compose run --rm web pytest -q
```

The packaged workspace passed 57 tests. Target-host results should be captured as local acceptance evidence.

For an upgrade, follow `UPGRADE_0.5.0.md`; do not delete named volumes.
