# LifeStats

Private, single-user Google Health companion. FastAPI owns domain behavior and integrations. Next.js renders Today. PostgreSQL stores local application data plus rebuildable Google Health projections.

## Runtime

- Python 3.13, FastAPI, SQLAlchemy async, Alembic
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
│       ├── core/
│       └── modules/
│           ├── identity/
│           ├── google_health/
│           ├── dashboard/
│           ├── scoring/
│           └── timeline/
└── web/src/
    ├── app/
    ├── lib/
    └── modules/
```

Backend modules are self-contained. Routers own HTTP mechanics, schemas own request/response validation, services own orchestration and business rules, and models own ORM mappings. Pure domain rules remain framework-independent. Google-specific transport stays inside its module.

## Source of truth

- Supported health writes go to Google Health first.
- Successful remote writes are reconciled into local projections.
- Local projection failure never overrides remote truth.
- Readiness, Stress, and Energy are transparent LifeStats estimates, not Google or Bevel scores.

## Local development

Requirements: Python 3.12+, Node.js 24, npm, PostgreSQL 17, Redis.

```bash
cp .env.example .env
uv sync --extra dev
npm install
uv run alembic upgrade head
uv run app
npm run dev
```

Run worker and scheduler separately:

```bash
uv run celery -A src.modules.google_health.tasks:celery_app worker --loglevel=INFO
uv run celery -A src.modules.google_health.tasks:celery_app beat --loglevel=INFO
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

## Safe cutover

Existing database contains irreplaceable health history.

1. Stop Laravel scheduler, worker, and all writes.
2. Take and verify PostgreSQL backup.
3. Preserve `TOKEN_ENCRYPTION_KEY`, `APP_KEY`, Google OAuth settings, and prior image.
4. Run `alembic upgrade head`; migration is additive and has no destructive downgrade.
5. Create private admin. Opening Google connection imports and re-encrypts legacy tokens without changing old rows.
6. Verify bound Google identity, projection counts, controlled sync, timeline, and scores.
7. Start Docker replacement. Keep old image and backup through rollback window.

Historical Laravel migrations remain unchanged in `database/migrations` as immutable safety records. Laravel runtime source has been removed; rollback uses the preserved prior image and database backup.

Future contexts—Fitness, meditation, food, biology, Alfred, Telegram, and Todoist—remain documentation-only until requested.
