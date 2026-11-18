# Agents Guide

## Purpose

This document is the working agreement for anyone—human or AI—developing Fashion Hub.

## Current project state

- Product context: to be defined as product requirements arrive.
- Repository: `ishandabri/fashion-hub`.
- UI foundation: shadcn/ui with a light, minimalistic visual language.
- Icons: use the shadcn-provided icon approach.
- Deployment target: containerized deployment.
- Product form: mobile-first progressive web app (PWA).

## Working rules

1. Read `prd.md`, `design.md`, `ui-ux.md`, and `steering.md` before making product or interface changes.
2. Prefer small, composable changes that preserve existing behavior.
3. Keep accessibility, responsive behavior, and clear empty/loading/error states in scope.
4. Reuse existing components and tokens before introducing new patterns.
5. Do not add dependencies without a clear need and a short note in the relevant documentation.
6. Update the living documents whenever a decision, requirement, flow, or implementation convention changes.
7. Before handing off work, verify the relevant user flow and report any known gaps.
8. Build and test the primary experience at mobile sizes first, then enhance for larger screens and installed PWA contexts.

## Environment conventions

- Use a local Python `venv` for Python development and tooling when Python is part of the stack.
- Keep dependency declarations reproducible and committed.
- Treat the deployment container as the production isolation boundary; do not nest a Python `venv` inside the container unless a concrete runtime constraint requires it.

## Documentation maintenance

When new product context is provided, update `prd.md` first, then reconcile `design.md`, `ui-ux.md`, and `steering.md`. Update this file when the development workflow or project-wide conventions change.

