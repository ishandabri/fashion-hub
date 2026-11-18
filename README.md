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

## Docker deployment

```bash
cp .env.example .env
docker compose up -d --build
```

The frontend binds to `127.0.0.1:8080`. Configure the host-managed Cloudflare Tunnel to route the HTTPS hostname to that local address. Keep tunnel credentials outside Git.

## Nightly backups

Configure `SOURCE_DB` and `BACKUP_DIR` for a mounted NAS or external-storage path, then run `scripts/backup_sqlite.py` from a host cron job or systemd timer. The script uses SQLite’s online backup API and retains seven backups.

## Current implementation status

The repository includes the initial runnable foundation, authentication bootstrap, daily sales, inventory add/sell/return flows, dashboard basics, PWA metadata, Docker configuration, and backup utility. Recurring expenses, other expenses, historical reporting, import/export, and expanded test coverage remain next implementation phases.

