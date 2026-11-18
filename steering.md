# Steering

This file records decisions that should guide future work. It is intentionally concise and should be updated when a decision changes.

## Decisions

| Area | Decision | Rationale |
| --- | --- | --- |
| Component system | Use shadcn/ui patterns and components | Keeps the interface composable, consistent, and easy to customize |
| Theme | Light theme by default | Establishes a clean, approachable baseline |
| Visual style | Minimalistic | Prioritizes products, content, and clear actions |
| Icons | Use the shadcn icon approach | Maintains a consistent, accessible icon language |
| Deployment | Use containers for deployment | Makes the production runtime reproducible and isolated |
| Product form | Build mobile-first as a progressive web app | Prioritizes the primary usage context and enables an installable web experience |
| Python development | Use a local `venv` when Python is involved | Keeps local dependencies isolated without nesting environments in production containers |
| Documentation | Keep project guidance and product artifacts current as the app develops | Prevents implementation drift |

## Pending decisions

- Product audience and primary job to be done.
- Core user journeys and MVP scope.
- Brand colors, typography, and image direction.
- Data model, integrations, and authentication requirements.
- Deployment target and analytics needs.

