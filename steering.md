# Steering

This document records project-wide decisions. Update it when a decision changes.

| Area | Decision |
| --- | --- |
| Product | A simple clothing-store P&L and inventory manager; not a POS, ERP, or billing system |
| Primary navigation | Exactly Dashboard, Entries, and Inventory |
| Product form | Mobile-first progressive web app, enhanced for desktop |
| UI system | shadcn/ui only, with reusable primitives and semantic tokens |
| Icons | shadcn-compatible icons only; no alternate icon library |
| Theme | Minimal light theme using a neutral shadcn palette and one restrained accent |
| Financial precision | Store money as integer paise; use exact calculations throughout |
| Business timezone | Asia/Kolkata dates; UTC timestamps |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, SQLite, Uvicorn |
| Frontend | React, strict TypeScript, Vite, Tailwind CSS, React Router, TanStack Query, React Hook Form, Zod, Recharts, date-fns, vite-plugin-pwa |
| Deployment | Docker and Docker Compose on Raspberry Pi 4 ARM64; persistent SQLite volume or bind mount |
| Authentication | One shared shop account for v1 with secure HTTP-only session cookies |
| Offline mode | Cache static assets only; financial data entry is online-only in v1 |
| Python environment | Use local `venv` for Python development; do not nest it in production containers by default |
| Documentation | Keep PRD, UX, design, steering, and agent guidance current as the app evolves |

## Explicit non-goals

- No manual monthly purchase or closing-stock entry.
- No item-level selling price or quantity field.
- No product category, size, colour, brand, supplier, or selling-price fields in v1.
- No Redis, Celery, PostgreSQL, external authentication service, microservices, or paid dependency.
- No complex offline synchronization.

