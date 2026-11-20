# Product Requirements Document

## Product

**Fashion Hub / Store Manager** is a mobile-first PWA for a small Indian clothing retail store. It records daily sales, tracks individual clothing inventory, calculates P&L, and explains inventory health. It is not a full ERP, POS, or billing system.

## Primary users and outcome

The primary user is a nontechnical shop owner using one secure shared shop login across multiple devices. The app must make daily entry take seconds while preserving accurate historical accounting.

## Scope

### Primary pages

1. **Dashboard** — current-month P&L, trends, comparisons, and inventory ageing.
2. **Entries** — Sales, Recurring Expenses, and Other Expenses tabs.
3. **Inventory** — item-level stock, sale/return events, ageing, and import.

Secondary settings, import/export, profile, and administration may use dialogs, drawers, or secondary routes.

### Daily sales

One total revenue amount per date. Fields: date and amount. Allow explicit zero-sales days, editing, viewing, correction, and confirmed deletion. Daily sales are independent revenue inputs and must never be generated from inventory sale events.

### Recurring expenses

Configure monthly expense rules with name, category, amount, effective start month, optional end month, and active status. Preserve historical rates through non-overlapping effective-dated versions. Support future changes, historical corrections with confirmation, pause, resume from the current business month, and end. V1 uses full-month amounts without daily proration.

### Other expenses

Record date, category, description, and amount on an accrual basis. Support custom categories, monthly/category filters, edit, delete with confirmation, and monthly totals.

### Inventory

Every physical item has a unique, case-insensitive normalized item code, purchase date, and purchase cost. Do not add notes, quantity, selling price, product metadata, or categories in v1.

Statuses are `IN_STOCK` and `SOLD`, backed by an immutable event history. Events include `PURCHASED`, `SOLD`, `SALE_REVERSED`, `RETURNED`, and `CORRECTION`.

Mark sold validates that the item is in stock, sale date is not before purchase or in the future, and no duplicate sale event exists. Reversal preserves the original sale event. A return validates chronology, restores stock, reverses COGS in the return month, preserves the original sale, and supports repeated sale/return cycles. Daily sales are not changed automatically.

Support CSV import with validation, duplicate detection, preview, row errors, transactional commit, optional status and sold date, and an explicit warning when historical records are incomplete.

Inventory listing supports debounced server-side prefix search by normalized item code and infinite scroll in batches of 25. The backend uses cursor-based continuation internally; the UI has no page controls and appends results as the user approaches the end of the list.

## Accounting rules

All money is INR. Store monetary values as integer paise. Use backend-derived reports as the authority; never store calculated monthly profit as authoritative.

- Monthly sales = daily sales totals in the month.
- Monthly purchases = purchase costs for items purchased in the month.
- Monthly COGS = item costs sold in the month minus item costs returned in the month.
- Gross profit = sales − COGS.
- Operating expenses = recurring expenses + other expenses.
- Net operating profit = gross profit − operating expenses.
- Gross margin = gross profit / sales × 100.
- Operating margin = net operating profit / sales × 100.
- Closing inventory = purchase cost of items owned and unsold at month end, based on historical state.
- Reconciliation: opening inventory + purchases − COGS = closing inventory, with warnings for exceptions.

Returned inventory affects the return period. A February sale and March return produce positive February COGS and negative March COGS; March closing inventory increases. Revenue refunds remain a separate daily-sales correction.

## Dashboard requirements

Default to the current calendar month in Asia/Kolkata with month/year selection. Show Total Sales, COGS, Gross Profit, Net Operating Profit, Closing Inventory Value, and Gross Profit Margin. Optional metrics include net margin, purchases, expenses, unsold count, and 90+ day stock.

Also show a monthly P&L statement, provisional indicator for the current month, last-12-month sales/gross-profit/net-profit trend, expense breakdown, 0–30/31–60/61–90/90+ ageing buckets, and month-over-month comparisons. Explicit zero-sales entries remain available when the shop owner knows a day had no sales; unrecorded dates are not treated as zero.

## INR formatting

Create shared exact-value utilities: `formatINR`, `formatCompactINR`, `formatPercentage`, and `formatIndianNumber`. Display with `Intl.NumberFormat("en-IN")`, rupee symbol, Indian digit grouping, and zero decimal places. Compact units are K, L, and Cr only, with safe boundary promotion and correct handling of zero, negatives, nulls, invalid values, and large amounts.

## Technical architecture

Frontend: React, strict TypeScript, Vite, Tailwind CSS, shadcn/ui, React Router, TanStack Query, React Hook Form, Zod, Recharts with shadcn chart components, date-fns, and vite-plugin-pwa.

Backend: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, SQLite, Uvicorn, and integer paise storage.

Infrastructure: Docker, Docker Compose, ARM64-compatible images, one API container and one frontend/reverse-proxy container where practical, persistent database storage, HTTPS-capable reverse proxy, health checks, environment configuration, and Raspberry Pi 4 / 4GB RAM compatibility.

## Data model

Use UUID-backed tables for `users`, `daily_sales`, `inventory_items`, `inventory_events`, `recurring_expenses`, `recurring_expense_versions`, `other_expenses`, `expense_categories`, `audit_logs`, and `import_batches`. Enforce foreign keys, WAL mode, busy timeout, indexes, transactional writes, normalized case-insensitive item codes, versioning, and complete audit history. Store UTC timestamps and separate ISO business dates.

## API surface

Prefix REST endpoints with `/api/v1`. Include secure auth endpoints, CRUD for sales and expenses, recurring-expense versioning/endpoints, inventory CRUD and event actions, report endpoints, CSV import preview/commit, and inventory/P&L export. Use Pydantic schemas, pagination, filtering, sorting, structured errors, status codes, backend validation, and optimistic concurrency.

## Security

Use Argon2id or equivalent password hashing, secure HTTP-only SameSite cookies, CSRF protection, login rate limiting, HTTPS in production, strict CORS, security headers, session expiry, logout, safe upload validation and size limits, parameterized queries, environment secrets, no frontend secrets, no debug endpoints, and safe errors without stack traces. Never expose SQLite directly.

## PWA and offline behavior

Use vite-plugin-pwa with Store Manager / Store naming, standalone display, theme/background colors, 192×192, 512×512, and maskable icons. Cache static assets only. Financial APIs remain online-only in v1. When offline, show connection state, disable writes, never fake success, and retry reads after reconnection.

## Deployment and recovery

Provide backend and frontend Dockerfiles, `docker-compose.yml`, `.env.example`, `.dockerignore`, and README instructions. Target Raspberry Pi 4 ARM64, nonroot containers where practical, restart policies, health checks, structured logs, persistent storage, LAN access, and secure remote access through an existing VPN or tunnel.

SQLite is the system of record. Implement safe daily online backups, retain 30 days, store outside the active database directory, support NAS/external storage, log outcomes, verify integrity, document restore, test restoration, and provide a manual backup/export option.

## Testing and acceptance

Use pytest/FastAPI TestClient/database integration tests, Vitest/React Testing Library, and Playwright. Cover purchases, sales, returns, reversals, backdating, expense versions, historical valuation/ageing, zero sales, negative profit, duplicate codes/events, chronology, reconciliation, currency boundaries, concurrency, imports, corrections, mobile navigation, validation, loading/empty/error states, responsive layouts, and keyboard accessibility.

The product is complete only when daily sales take seconds, inventory and events are accurate, historical reports remain correct, INR formatting is exact, the PWA installs on supported mobile devices, the app runs in Docker on Raspberry Pi ARM64, financial data is protected, backups work, and setup/deployment/restore documentation is complete.

## Change log

- Product specification incorporated from the clothing-store P&L and inventory PWA brief.
- Final icon decision: shadcn-compatible icons only.

