# Fashion Hub

Mobile-first clothing-store P&L and inventory PWA.

## Local development

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".\backend[test]"
Copy-Item .env.example .env
alembic -c backend/alembic.ini upgrade head
uvicorn app.main:app --app-dir backend --reload --port 8000
```

### Frontend

```powershell
corepack enable
cd frontend
pnpm install
pnpm dev
```

The frontend runs on port 5173 and proxies `/api` to the backend on port 8000.

## Testing

Run backend API and accounting tests:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

Run frontend unit tests and build:

```powershell
npx --yes pnpm@9.15.0 --dir frontend test
npx --yes pnpm@9.15.0 --dir frontend build
```

Run Playwright end-to-end tests against the local Docker stack. Install browsers once with `frontend\node_modules\.bin\playwright.cmd install chromium webkit`:

```powershell
npx --yes pnpm@9.15.0 --dir frontend exec playwright test
```

The suite covers authentication, dashboard/P&L visibility, primary navigation, expense tabs, inventory entry, mobile layout, and desktop layout.

## Docker deployment

```bash
cp .env.example .env
docker compose up -d --build
```

The API container applies Alembic migrations before starting. Deployments do not create a database backup before migrations. A migration will stop without changing data if it finds overlapping or non-month-start recurring-expense versions; correct those records deliberately before retrying. Automatic code rollback is skipped when migration files changed.

The frontend binds to `127.0.0.1:6001`. Configure the host-managed Cloudflare Tunnel to route the HTTPS hostname to that local address. Keep tunnel credentials outside Git.

### Make commands

The root `Makefile` supports both local Docker use and Raspberry Pi deployment. Set `DEPLOY_TARGET=local` for the local stack; the default target is `raspi`. Local Docker runs explicitly with `APP_ENV=development` because HTTPS is not available locally; Raspberry Pi deployments explicitly run with `APP_ENV=production`.

```bash
# Local Docker stack
make preflight DEPLOY_TARGET=local
make deploy DEPLOY_TARGET=local
make local-down

# Raspberry Pi (deploy an annotated SemVer tag)
git tag -a v0.1.1 -m "Release v0.1.1"
git push origin v0.1.1
make preflight RELEASE_TAG=v0.1.1 RASPI_HOST=raspi RASPI_REPO_PATH=/home/ishan/projects/fashion-hub
make deploy RELEASE_TAG=v0.1.1 RASPI_HOST=raspi RASPI_REPO_PATH=/home/ishan/projects/fashion-hub
# Explicit rollback to a known-good release
make rollback RELEASE_TAG=v0.1.0 RASPI_HOST=raspi RASPI_REPO_PATH=/home/ishan/projects/fashion-hub
# Inspect deployment state and API build identity
make status RASPI_HOST=raspi RASPI_REPO_PATH=/home/ishan/projects/fashion-hub
# Inspect silent PWA update failures
make logs-api RASPI_HOST=raspi RASPI_REPO_PATH=/home/ishan/projects/fashion-hub
```

For repeat use, put non-secret deployment settings in `.env.deploy` (ignored by Git), for example `RASPI_HOST` and `RASPI_REPO_PATH`. The remote `.env` must be created from `.env.example` and contain the production bootstrap password. Deploying a previous tag is the rollback procedure.

The PWA checks for a new service worker once when the app is opened or the page is loaded, and once when a suspended installed PWA returns to the foreground. A ready release activates and reloads automatically; an app that remains open is updated on its next launch. Build version, Git revision, and UTC build time are available at the authenticated, unlinked `/diagnostics` route.

Codex manages release tags when a deployment is requested. It selects patch/minor SemVer according to the change type, asks before major releases, updates the synchronized release metadata, creates and pushes the annotated tag, then deploys that exact tag. Normal code changes are not tagged automatically.

## Nightly backups

Install the files in `deployment/systemd/` as host-level scripts and systemd units on the Raspberry Pi. The backup timer runs daily at 07:00 IST and writes verified SQLite backups to `/mnt/WebAppsBkp/fashion-hub`, retaining 3 daily backups. The restore-verification timer runs on the first day of each month.

The systemd service expects the application at `/home/ishan/projects/fashion-hub`; update the `SOURCE_DB` and `WorkingDirectory` values if the deployment path differs. The backup service must run only after the `/mnt/WebAppsBkp` mount is available. It stages and verifies the SQLite backup locally at `/var/lib/fashion-hub-backup` before copying the completed artifact to the backup share, which avoids SQLite locking issues on CIFS/SMB mounts.

## Current implementation status

The repository includes the initial runnable foundation, authentication bootstrap, daily sales, recurring and other expenses, effective-month recurring-expense pauses, inventory add/sell/return flows, dashboard basics, PWA metadata, Docker configuration, and systemd backup/restore-verification units. Historical reporting, import/export, and expanded test coverage remain next implementation phases.
