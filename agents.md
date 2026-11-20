# Agents Guide

## Mission

Build and maintain a production-ready, mobile-first PWA for a small Indian clothing retailer. The product is a simple daily-management tool for sales, inventory, expenses, P&L, and stock health—not a full ERP, POS, or billing system.

## Source of truth

Before changing product behavior or UI, read `prd.md`, `steering.md`, `design.md`, and `ui-ux.md`. Keep all four synchronized whenever requirements, accounting rules, architecture, or interaction patterns change.

## Non-negotiable conventions

- Mobile-first responsive PWA; exactly three primary pages: Dashboard, Entries, Inventory.
- Light, minimalistic shadcn/ui system with semantic CSS variables and reusable components.
- Use shadcn-compatible icons only. Do not introduce alternate icon libraries.
- All money is INR and must be calculated exactly using integer paise or equivalent decimal-safe representations.
- Backend calculations are authoritative; do not duplicate accounting logic in frontend components.
- Preserve dated records and event history. Never destroy original sale, return, correction, or audit history.
- Use Asia/Kolkata for business dates and UTC timestamps for system timestamps.
- Use a local Python `venv` for Python development. The deployment container is the production isolation boundary; do not nest a `venv` in production images by default.
- Use Docker Compose for Raspberry Pi 4 ARM64 deployment with persistent SQLite storage and backups.

## Engineering rules

1. Centralize business rules in backend services and reporting queries.
2. Use database transactions for inventory state changes and imports.
3. Use optimistic concurrency with version numbers for edits.
4. Keep forms small, accessible, touch-friendly, and reusable.
5. Include loading, empty, error, offline, and confirmation states.
6. Do not use mock data or localStorage for production functionality.
7. Do not add modules, paid services, or infrastructure that the PRD does not require.
8. Run type checks, linting, relevant tests, and a production build after changes.
9. Update documentation before implementation when an assumption is needed.

## Release management

- Codex owns release tags when the user authorizes a deployment.
- Use annotated SemVer tags in the form `vMAJOR.MINOR.PATCH`.
- Choose patch releases for fixes and maintenance, minor releases for backward-compatible features, and ask before creating a major release.
- Update synchronized frontend, backend, and API release metadata, run verification, create and push the annotated tag, then deploy that exact tag to the Raspberry Pi.
- Do not create a pre-migration database backup as part of deployment; use the scheduled backup process separately.
- Log silent PWA update failures to rotated container logs without showing them in the user interface.
- Do not create or push tags for ordinary implementation work unless deployment is requested.

## Implementation order

1. Foundation and authentication.
2. Inventory, events, import, and ageing.
3. Daily sales and expenses.
4. Reports and dashboard.
5. PWA, security hardening, backups, Docker deployment, tests, and documentation.

