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
├── api/src/lifestats/
│   ├── identity/
│   ├── google_health/
│   ├── dashboard/
│   ├── scoring/
│   ├── timeline/
│   ├── habits/
│   └── shared_kernel/
└── web/src/
    ├── app/
    ├── lib/
    └── modules/
```

Backend contexts own `domain`, `application`, `infrastructure`, and `presentation`. Domain code is framework-independent. Cross-context behavior uses application contracts. Architecture tests reject imports of another context’s infrastructure.

## Source of truth

- Supported health writes go to Google Health first.
- Successful remote writes are reconciled into local projections.
- Local projection failure never overrides remote truth.
- Habits unsupported by Google remain local.
- Readiness, Stress, and Energy are transparent LifeStats estimates, not Google or Bevel scores.

## Local development

Requirements: Python 3.12+, Node.js 24, npm, PostgreSQL 17, Redis.

```bash
cp .env.example .env
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
npm install
alembic upgrade head
uvicorn lifestats.main:app --app-dir apps/api/src --reload
npm run dev
```

Run worker and scheduler separately:

```bash
celery -A lifestats.google_health.infrastructure.celery_app:celery_app worker --loglevel=INFO
celery -A lifestats.google_health.infrastructure.celery_app:celery_app beat --loglevel=INFO
```

Open `http://localhost:3000`. First setup requires `SETUP_TOKEN`. After account creation, setup permanently returns 404.

## Verification

```bash
ruff check .
ruff format --check .
mypy
pytest
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
6. Verify bound Google identity, projection counts, controlled sync, timeline, habits, and scores.
7. Start Docker replacement. Keep old image and backup through rollback window.

Historical Laravel migrations remain unchanged in `database/migrations` as immutable safety records. Laravel runtime source has been removed; rollback uses the preserved prior image and database backup.

Future contexts—Fitness, meditation, food, biology, Alfred, Telegram, and Todoist—remain documentation-only until requested.
