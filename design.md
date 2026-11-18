# Design System

## Direction

Minimal, light, neutral, content-first, and editorial. Use whitespace, subtle grey borders, clean cards, minimal shadows, neutral text, and one restrained primary accent. Do not use gradients, glassmorphism, or decorative clutter.

## Foundation

- Component system: shadcn/ui only.
- Icons: shadcn-compatible icons only.
- Typography: clean system font or Inter.
- Product form: mobile-first progressive web app.
- Financial figures: tabular numerals.

## Semantic tokens

Define all colors through CSS variables and Tailwind theme tokens. Required tokens include `background`, `foreground`, `card`, `card-foreground`, `popover`, `popover-foreground`, `primary`, `primary-foreground`, `secondary`, `secondary-foreground`, `muted`, `muted-foreground`, `accent`, `accent-foreground`, `destructive`, `border`, `input`, `ring`, `chart-1` through `chart-5`, and `radius`.

Financial tokens: `financial-positive`, `financial-negative`, `financial-warning`, and `financial-neutral`.

Never hardcode component-level hex colors.

## Layout tokens

- `page-container`: max-width 1280px, centered.
- `form-container`: max-width 560px.
- `dialog-container`: responsive, max-width 480px.
- `table-container`: full available width.
- Mobile content padding: 16px.
- Desktop content padding: 24px.
- Section gap: 24px.
- Card gap: 16px.

## Type scale

- Page title: 24px semibold.
- Section title: 18px semibold.
- Card title: 14px medium.
- KPI value: 24–30px semibold.
- Body: 14px.
- Helper text: 12px.
- Table values: 14px.

## Shared components

Build and reuse `AppLayout`, `PageHeader`, `PageContainer`, `FormField`, `CurrencyInput`, `DateField`, `SearchField`, `ConfirmDialog`, `KpiCard`, `CurrencyDisplay`, `MonthSelector`, `EmptyState`, `LoadingState`, `ErrorState`, `StatusBadge`, `ResponsiveDataTable`, and `InventoryAgeBadge`.

Use shadcn primitives such as Button, Card, Input, Label, Select, Tabs, Dialog, AlertDialog, Sheet, Popover, Calendar, Table, Badge, Separator, Skeleton, Sonner, DropdownMenu, Tooltip, and Chart where appropriate.

