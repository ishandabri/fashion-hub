# UI/UX Guidelines

## Experience goal

Make daily work fast and obvious for a nontechnical shop owner. The interface should feel calm, lightweight, and trustworthy while making financial state and inventory health easy to understand.

Dashboard hierarchy: keep the month control right-aligned in the Dashboard title row; show only Sales and Operating profit KPI cards, followed by inventory ageing and the 12-month P&L chart. Keep the Monthly P&L table, expense breakdown, and reconciliation behind the existing detailed-reports disclosure. Do not show an unsold-items KPI or a separate ageing attention panel.

## Navigation

- Mobile: fixed bottom navigation with Dashboard, Entries, and Inventory.
- Desktop: compact sidebar or top navigation.
- Use icon plus label, visible active state, safe-area padding, and minimum 44px touch targets.
- Keep content clear of the fixed mobile navigation.
- Settings, import/export, profile, and administration belong in secondary routes, dialogs, drawers, or a settings menu.

## Core flows

- Daily sales: date and total amount; default to today in Asia/Kolkata; one record per date; edit existing dates instead of duplicating.
- Inventory: rapid three-field item entry; preserve the last purchase date after save; never repeat purchase price automatically.
- Inventory search: place an item-code search field at the top of the page, search as typed with a short debounce, show prefix matches from the server, and append additional records automatically as the user scrolls. Use loading, empty, no-match, and error states.
- Inventory toolbar: keep Search, Status, Import, and Export together in one desktop row. Import opens a file-selection dialog with Browse; Preview validates the CSV and shows row-level results before any commit.
- Mark sold: confirm item details and sale date; validate chronology; never create revenue automatically.
- Return or reverse: preserve original events, require confirmation, update historical reports, and explain that daily sales must be corrected separately.
- Expenses: use tabs for Sales, Recurring Expenses, and Other Expenses.

## Responsive behavior

- Design and validate mobile first, then enhance for desktop.
- Use compact item cards or responsive tables on mobile; avoid horizontal scrolling.
- Keep desktop forms readable with a shared form max width of 560px.
- Preserve content hierarchy when grids and tables collapse.
- Keep the 12-month P&L chart at a compact fixed height with abbreviated month labels and exact values available on interaction; it must not require horizontal scrolling.
- Respect iOS safe areas, viewport behavior, touch targets, keyboard navigation, and visible focus.

## PWA behavior

- Installable manifest with Store Manager / Store naming, standalone display, theme and background colors, 192px, 512px, and maskable icons.
- Cache static application assets where appropriate.
- Do not cache authenticated financial API responses for offline use.
- Show connection status and a friendly offline screen; disable writes offline and never claim a save succeeded.
- Retry reads when connectivity returns.

## States and accessibility

Every data-driven view needs loading, empty, error, success, and provisional-data states. Destructive actions require confirmation. Warnings must be non-blocking unless the action is unsafe. Use accessible labels, semantic controls, keyboard support, clear validation, and color-independent status communication.

Modal dialogs use the top-right X as their dismissal control; do not repeat it with a footer Cancel button. Keep meaningful secondary actions such as Delete and Retry visible.

Recurring expenses use a pause icon for active rules and a play icon for paused rules. Resuming takes effect from the current business month and preserves the pause interval in history.

