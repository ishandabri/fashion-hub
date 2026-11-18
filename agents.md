# Agents Guide

## Purpose

This document is the working agreement for anyone—human or AI—developing Fashion Hub.

## Current project state

- Product context: to be defined as product requirements arrive.
- Repository: `ishandabri/fashion-hub`.
- UI foundation: shadcn/ui with a light, minimalistic visual language.
- Icons: use the shadcn-provided icon approach.

## Working rules

1. Read `prd.md`, `design.md`, `ui-ux.md`, and `steering.md` before making product or interface changes.
2. Prefer small, composable changes that preserve existing behavior.
3. Keep accessibility, responsive behavior, and clear empty/loading/error states in scope.
4. Reuse existing components and tokens before introducing new patterns.
5. Do not add dependencies without a clear need and a short note in the relevant documentation.
6. Update the living documents whenever a decision, requirement, flow, or implementation convention changes.
7. Before handing off work, verify the relevant user flow and report any known gaps.

## Documentation maintenance

When new product context is provided, update `prd.md` first, then reconcile `design.md`, `ui-ux.md`, and `steering.md`. Update this file when the development workflow or project-wide conventions change.

