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

- Backend bounded contexts live under `apps/api/src/lifestats/<context>`.
- Each context owns `domain`, `application`, `infrastructure`, and `presentation` layers.
- Dependencies point `presentation → application → domain`.
- Domain code must not import FastAPI, SQLAlchemy, HTTPX, Celery, provider payloads, or another context's infrastructure.
- Cross-context behavior uses semantic application ports or domain events.
- Provider-specific code stays inside `google_health`.
- Next.js route composition lives under `apps/web/src/app`; feature UI stays under `apps/web/src/modules`.
- Frontend contracts come from the FastAPI OpenAPI schema.

## Frontend design

- Follow `docs/UI_UX_SYSTEM_DESIGN.md` for tokens, components, states, responsive behavior, accessibility, and content voice.
- Keep primary navigation limited to Today, Fitness, Sleep, and Health.
- Never use color alone to judge health values or communicate state.

## Data safety

- Never reset or drop an existing LifeStats database.
- Never delete or rewrite historical migrations during feature cleanup.
- Use additive Alembic migrations.
- Preserve legacy token decryption and historical tables until rollback windows explicitly end.

## Quality gate

Run before handoff:

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy
.venv/bin/pytest
npm run lint
npm run typecheck
npm run build
npm run openapi:check
```

Production changes must also pass empty/legacy PostgreSQL migration tests and the Docker build.
