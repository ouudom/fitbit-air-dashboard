# LifeStats UI/UX system design

This document defines frontend design rules for the LifeStats Google Health companion. It adapts the supplied telemetry design into an original, private health dashboard. Product structure follows `docs/GOOGLE_HEALTH_CLONE_PLAN.md`.

## 1. Design direction

LifeStats uses a dark, precise, data-first interface. It should feel calm, trustworthy, and fast—not military, gamified, or diagnostic.

Core principles:

1. **Low-light comfort:** dark surfaces, restrained brightness, strong text contrast.
2. **Source clarity:** show source, freshness, missing permission, and sync state near health data.
3. **Data before decoration:** charts and useful context earn space. Decorative cards do not.
4. **Flat hierarchy:** avoid cards nested inside cards. Use spacing and dividers first.
5. **No invented health judgment:** colors communicate UI state, not whether a health value is medically good or bad.
6. **Original identity:** borrow useful information architecture, never Google branding, artwork, or proprietary score presentation.

## 2. Product navigation

Exactly four primary destinations:

| Destination | Route | Purpose |
| --- | --- | --- |
| Today | `/dashboard` | Latest focus metrics, recent sessions, sync freshness |
| Fitness | `/fitness` | Activity, energy, distance, zone minutes, workouts |
| Sleep | `/sleep` | Sessions, duration, stages, schedule, supported trends |
| Health | `/health` | Vitals, heart, measurements, nutrition, hydration |

Desktop uses a compact top navigation until content density proves a side rail necessary. Mobile uses a persistent four-item bottom bar. Minimum touch target: `44px × 44px`.

Secondary pages, such as nutrition, remain children of one primary destination. They never become extra primary tabs.

## 3. Typography

Use locally available fonts. Avoid adding a remote-font runtime dependency.

- Product text: `Instrument Sans`, `ui-sans-serif`, `system-ui`, `sans-serif`.
- Numeric and diagnostic text: `ui-monospace`, `SFMono-Regular`, `Menlo`, `monospace`.
- Use tabular numerals for metrics, timestamps, and chart values.

| Role | Size | Weight | Tracking | Use |
| --- | --- | --- | --- | --- |
| Page title | `28px` | `750` | `-0.03em` | Current destination |
| Section title | `18px` | `700` | `-0.01em` | Major content group |
| Card title | `14px` | `650` | normal | Metric or widget name |
| Metric | `28–32px` | `750` | `-0.02em` | Primary numeric value |
| Label | `11px` | `700` | `0.06em` | Metadata, table headers |
| Body | `13px` | `450` | normal | Explanations and status |
| Caption | `11px` | `500` | normal | Source, unit, freshness |

Rules:

- Buttons and primary navigation labels stay on one line.
- Body copy uses a maximum width of `65ch`.
- Units remain visually subordinate but readable.
- Never encode state using typography or color alone.

## 4. Layout and spacing

Use a 4px base grid:

- `4px`: icon/label micro-gap.
- `8px`: related controls.
- `12px`: compact row spacing.
- `16px`: standard component padding.
- `24px`: section separation.
- `32px`: page-level separation.

Page container: `1120px` maximum width with `24px` desktop gutters and `16px` mobile gutters.

Grid behavior:

- Desktop: four metric columns, two content columns where useful.
- Tablet: two metric columns.
- Mobile: one metric column when values or labels would compress.
- Tables become horizontally scrollable only when a list/card alternative loses important comparison value.

Maximum visual nesting:

1. Canvas.
2. Panel.
3. Input or diagnostic cell.

Nested corner radius follows the available inset. Do not place a large rounded card inside another large rounded card.

## 5. Color tokens

Dark mode is the baseline. Tokens must be CSS custom properties; components must not hard-code palette values.

```css
:root {
    color-scheme: dark;
    --canvas: #0f1113;
    --surface: #171a1e;
    --surface-raised: #1d2126;
    --surface-inset: #121416;
    --border: #30353d;
    --text: #e7ebf0;
    --text-muted: #98a3b1;
    --accent: #e4bd4f;
    --accent-strong: #f2c94c;
    --success: #5cc979;
    --info: #6f93bd;
    --warning: #e0a657;
    --danger: #ef6a6a;
    --sleep-light: #7399be;
    --sleep-deep: #566d9f;
    --sleep-rem: #9a7fbb;
    --sleep-awake: #c98a68;
}
```

Semantic rules:

- Accent marks selected navigation and primary actions.
- Success means operation succeeded or source is connected. It does not mean a health value is healthy.
- Danger means failure, destructive action, or unavailable connection. It does not diagnose risk.
- Sleep-stage colors remain consistent across every chart and legend.
- Text and interactive controls must meet WCAG 2.2 AA contrast.

## 6. Core components

### 6.1 Application shell

- Compact sticky header on desktop.
- Four-item bottom navigation on mobile.
- User and logout controls remain secondary.
- Sync status is visible from Today without becoming a primary navigation item.
- Content must not hide behind the mobile bottom bar.

### 6.2 Metric card

Each metric card contains:

1. Metric label.
2. Value and unit.
3. Measurement date or range.
4. Freshness or availability state when needed.
5. Link to detail only when a detail view exists.

Never render a fake zero for missing data. Use an em dash and a reason such as `Not synced`, `Permission missing`, or `Not available through API`.

### 6.3 Panels

- One title and optional description.
- Optional action aligned opposite title.
- One primary information purpose.
- Use a divider instead of another bordered card for internal rows.

### 6.4 Charts

- Always include title, unit, date range, and accessible text summary.
- Tooltips work with keyboard and pointer input.
- Missing values create gaps; they do not become zero.
- Do not smooth lines when smoothing could imply measurements that never existed.
- Avoid red/green comparisons for health values.
- Provide a table or text alternative for dense telemetry.

### 6.5 Source status

Standard states:

| State | Message behavior |
| --- | --- |
| Fresh | Show last successful sync quietly |
| Syncing | Disable duplicate sync; show progress without layout shift |
| Stale | Keep cached value; clearly show age |
| Permission missing | Explain required Google Health permission |
| Unsupported | Say metric is unavailable through current API |
| Failed | Preserve last good value and show retry action |
| Empty | Explain whether user needs data, permission, device, or sync |

### 6.6 Forms

- Persist supported health writes to Google Health first.
- Show remote failure before implying success locally.
- Labels remain visible; placeholders are examples only.
- Validation appears near the field and in a concise page-level error summary.
- Destructive actions require explicit confirmation.

## 7. Motion

Motion is short and functional:

- Hover/focus transition: `120ms`.
- Page/content reveal: `150ms`, maximum `4px` translation.
- Drawer transition: `200ms` ease-out.
- Sync indicator: linear rotation while active.
- No bounce, elastic easing, parallax, or ambient looping animation.
- Respect `prefers-reduced-motion` and remove nonessential movement.

## 8. Responsive rules

### Desktop

- Keep four destinations visible.
- Use multi-column layouts only when comparison improves understanding.
- Charts receive more space than decorative summary content.
- Avoid permanent side navigation during base implementation.

### Mobile

- Persistent four-tab bottom bar.
- Single-column reading order.
- Header prioritizes page title and sync state.
- Tables prefer summarized cards, with details behind progressive disclosure.
- Actions remain reachable with one hand and clear the safe-area inset.

## 9. Accessibility

- Semantic landmarks: header, navigation, main, section.
- One visible `h1` per page; headings never skip hierarchy.
- Strong focus-visible indicator on every control.
- Icon-only controls require accessible names.
- Status updates use appropriate `role="status"`; errors use `role="alert"` sparingly.
- Charts cannot be the only way to understand a value.
- Screen readers receive metric value, unit, date, source, and availability.
- Zoom to 200% without lost content or horizontal page scrolling.

## 10. Content voice

Use concise, literal language:

- `Last synced 8 minutes ago`
- `Google Health permission required`
- `No sleep session synced`
- `Not available through Google Health API`

Avoid medical conclusions, motivational pressure, tactical language, and invented certainty:

- Do not say `optimal`, `poor`, `dangerous`, or `recovered` without an authoritative source field and clear context.
- Do not describe sync as an uplink, telemetry command, or secure packet operation.
- Do not present locally calculated readiness, recovery, strain, stress, energy, or sleep scores.

## 11. Definition of done

A frontend change is complete when:

- It fits Today, Fitness, Sleep, or Health.
- It uses shared tokens and components.
- Loading, empty, stale, unsupported, permission, and error states are handled where applicable.
- Mobile and desktop layouts work.
- Keyboard and screen-reader paths work.
- Source and freshness are not ambiguous.
- No local projection is presented as authoritative Google Health data.
- `npm run build` and `npx tsc --noEmit` pass.

