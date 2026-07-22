# CLAUDE.md

Read and follow `AGENTS.md` first.

For frontend work, also follow `docs/UI_UX_SYSTEM_DESIGN.md`.

## Current objective

Rebuild LifeStats around the base Google Health app experience. Target the device-connected four-tab product: Today, Fitness, Sleep, and Health.

Google Health API is source of truth. PostgreSQL stores synchronized projections for fast rendering; it is not an independent authority for Google Health records.

## Current scope

Build in this order:

1. Reliable OAuth, sync status, freshness, and error recovery.
2. Today focus metrics and recent sessions.
3. Fitness activity metrics and workout history.
4. Sleep duration, stages, schedule, and quality metrics supported by the API.
5. Health vitals, heart, metabolic measurements, nutrition, and hydration supported by the API.
6. Metric details and source-backed trends.

Exclude for the base milestone:

- Google Health Coach and all premium functionality.
- Custom recovery, strain, stress, and energy scores.
- Local habit journal.
- Local strength-session logger.
- Social, friends, leaderboards, badges, community, and messaging.
- Cycle health until Google Health API support is available and explicitly selected.

## Implementation boundaries

- Do not copy Google trademarks, proprietary artwork, or private algorithms.
- Reproduce information architecture and supported workflows using original LifeStats styling.
- Do not reverse engineer official readiness or sleep score formulas.
- API availability wins over UI parity. Mark unsupported features in the plan instead of fabricating data.
- Keep removed-feature tables intact. Remove routes, controllers, services, UI, bindings, and tests only.

## Useful commands

```bash
php artisan module:list
php artisan route:list --except-vendor
php artisan schedule:list
composer test
npm run build
npx tsc --noEmit
./vendor/bin/pint --test
```
