# LifeStats

Private, single-user Google Health companion. FastAPI owns domain behavior and integrations. Next.js renders Today. PostgreSQL stores local application data plus rebuildable Google Health projections.

## Runtime

- Python 3.12+, FastAPI, SQLAlchemy async, Alembic
- Celery and Redis for sync work
- Next.js, React, TypeScript, TanStack Query
- PostgreSQL 17
- Caddy same-origin proxy

## Modular DDD

```text
apps/
├── api/
│   ├── alembic/
│   └── src/
│       ├── __init__.py
│       ├── main.py
│       ├── api/
│       │   └── router.py
│       ├── core/
│       └── modules/
│           ├── auth/
│           ├── google_health/
│           ├── dashboard/
│           └── timeline/
└── web/src/
    ├── app/
    ├── lib/
    └── modules/
```

`main.py` creates the application. `api/router.py` composes module routers.
Backend modules are self-contained. Routers own HTTP mechanics, schemas own
request/response validation, services own orchestration and business rules,
repositories own database queries, and models own ORM mappings. Pure domain
rules remain framework-independent. Google-specific transport, registry, sync
tasks, and persistence stay inside its module. Dashboard remains a first-class
module and `/api/v1/dashboard` route.

## Source of truth

- Supported health writes go to Google Health first.
- Successful remote writes are reconciled into local projections.
- Local projection failure never overrides remote truth.

## Local development

Requirements: Python 3.12+, Node.js 24, npm, and OrbStack.

```bash
cp .env.example .env
uv sync --extra dev
npm install
uv run alembic upgrade head
uv run app
npm run dev
```

Run PostgreSQL, Redis, API, Celery worker, Celery scheduler, web, and proxy with OrbStack:

```bash
docker compose up -d --build
docker compose ps
```

Open `http://localhost:3000`. First setup requires `SETUP_TOKEN`. After account creation, setup permanently returns 404.

## Verification

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
npm run lint
npm run typecheck
npm run build
npm run openapi:check
docker compose build
```

## Fresh database cutover

`20260723_0001_init` is a fresh PostgreSQL baseline. It does not import the old
database.

1. Stop existing writers.
2. Back up and restore-test the old PostgreSQL database.
3. Preserve encryption keys, Google OAuth settings, and prior image.
4. Start a new `lifestats` database or volume.
5. Run `uv run alembic upgrade head`.
6. Create the private account and reconnect Google Health.
7. Start worker and scheduler; verify 39 sync jobs and initial polling.
8. Keep webhooks disabled until polling and signature tests pass.
9. Run `google-health-subscriber inspect`, then `apply`.
10. Keep the old database and image through the rollback window.

Future contexts—Fitness, meditation, food, biology, Alfred, Telegram, and Todoist—remain documentation-only until requested.
