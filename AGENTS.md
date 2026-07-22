# LifeStats agent instructions

## Product target

Build a private web companion modeled on the post-May 2026 Google Health app. Google Health API is the authoritative source for health, fitness, sleep, nutrition, and measurement data.

The base product has four primary sections:

- Today
- Fitness
- Sleep
- Health

Do not add Google Health Premium, Coach, social, badges, community, or speculative medical features unless explicitly requested.

## Source-of-truth rules

- Write supported data to Google Health first.
- Read it back through Google Health sync.
- Treat local health tables as rebuildable projections and caches.
- Never let local health rows silently override Google Health.
- Never present a locally invented score as an official Google Health score.
- If an official metric is unavailable through the API, show it as unavailable and document the gap.
- `User` and application authentication remain core concerns.
- Historical tables and migrations may remain for data safety even after their product feature is removed.

## Architecture

- Keep provider-specific code inside `Modules/GoogleHealth`.
- Keep shared contracts and `User` under `app`.
- Core code may depend on contracts. Core code must not import `Modules\\GoogleHealth` implementations.
- Module folders, namespaces, and classes use StudlyCase: `GoogleHealth`.
- Module aliases, config keys, and asset slugs use kebab-case: `google-health`.
- Module-owned Inertia pages live under `Modules/<Module>/resources/js/Pages`.
- Shared React components, layouts, and types remain under `resources/js`.
- Prefer semantic ports such as `NutritionLogWriter`; never expose Google wire payloads through core contracts.

## Frontend design

- Follow `docs/UI_UX_SYSTEM_DESIGN.md` for tokens, components, states, responsive behavior, accessibility, and content voice.
- Keep primary navigation limited to Today, Fitness, Sleep, and Health.
- Never use color alone to judge health values or communicate state.

## Data safety

- Never run `migrate:fresh` against an existing LifeStats database.
- Never delete or rewrite historical migrations during feature cleanup.
- Use additive migrations.
- Preserve legacy token encryption and queued-job compatibility until their rollback windows explicitly end.

## Quality gate

Run before handoff:

```bash
composer validate --strict
./vendor/bin/pint --test
composer test
npm run build
npx tsc --noEmit
php artisan optimize
```

Production changes must also pass the Docker build and an in-image `php artisan optimize` check.
