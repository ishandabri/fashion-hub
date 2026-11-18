# Fashion Hub

Mobile-first clothing-store P&L and inventory PWA.

## Local development

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".\backend[test]"
Copy-Item .env.example .env
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

The frontend binds to `127.0.0.1:6000`. Configure the host-managed Cloudflare Tunnel to route the HTTPS hostname to that local address. Keep tunnel credentials outside Git.

## Nightly backups

Install the files in `deployment/systemd/` as host-level scripts and systemd units on the Raspberry Pi. The backup timer runs daily at 07:00 IST and writes verified SQLite backups to `/mnt/WebAppsBkp/fashion-hub`, retaining 3 daily backups. The restore-verification timer runs on the first day of each month.

The systemd service expects the application at `/home/ishan/projects/fashion-hub`; update the `SOURCE_DB` and `WorkingDirectory` values if the deployment path differs. The backup service must run only after the `/mnt/WebAppsBkp` mount is available.

## Current implementation status

The repository includes the initial runnable foundation, authentication bootstrap, daily sales, inventory add/sell/return flows, dashboard basics, PWA metadata, Docker configuration, and systemd backup/restore-verification units. Recurring expenses, other expenses, historical reporting, import/export, and expanded test coverage remain next implementation phases.
