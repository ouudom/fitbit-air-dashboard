# LifeStats

Personal health dashboard. Laravel serves Inertia pages and owns shared persistence and scoring. Feature modules own external integrations. React renders dashboard UI. PostgreSQL schema remains compatible with the earlier deployment.

## Stack

- PHP 8.5
- Laravel 13
- Inertia 3
- React 19 + TypeScript
- Vite 8
- PostgreSQL 17
- FrankenPHP production runtime
- nwidart/laravel-modules 13

## Modular structure

```text
app/
├── Domain/
│   ├── Analytics/   # queries, wellness scoring, journal insights
│   ├── Coach/       # provider boundary, context, response streaming
│   └── Health/      # provider-neutral integration contracts
├── Http/
│   ├── Controllers/ # shared Inertia and mutation endpoints
│   └── Middleware/  # shared Inertia props
└── Models/          # users and normalized application data
Modules/
└── GoogleHealth/
    ├── app/          # API, OAuth, sync, jobs, models, HTTP, providers
    ├── config/       # google-health.* configuration
    ├── database/     # future module migrations, factories, seeders
    ├── resources/js/ # module-owned Inertia pages
    ├── routes/       # module-owned web/API routes
    ├── tests/        # module feature and unit tests
    ├── composer.json
    └── module.json
resources/js/
├── components/      # reusable UI and chart primitives
├── layouts/         # application shell
├── pages/           # shared route-level Inertia pages
└── types/           # shared TypeScript contracts
```

Module folders and PHP namespaces use StudlyCase (`GoogleHealth`). Aliases, configuration keys, routes, and asset slugs use kebab-case (`google-health`). Core code depends only on contracts under `app/Domain`; module providers bind those contracts to integration implementations. `User`, normalized health records, metrics, scores, and shared UI stay in the main application.

`GoogleHealth` is a required integration module for the current authentication and nutrition workflows. Keep `modules_statuses.json` deployed with `"GoogleHealth": true`. Application boot fails clearly when its required contract is unavailable; `module:*` commands remain available for recovery.

Historical schema remains in the root migration for upgrade safety. Future Google-specific schema changes belong in `Modules/GoogleHealth/database/migrations`.

## Local setup

Requirements: PHP 8.5 with PDO PostgreSQL, Composer 2, Node.js 22, npm, PostgreSQL 17.

```bash
cp .env.example .env
composer install
npm install
php artisan key:generate
php artisan migrate
composer run dev
```

Set `DATABASE_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `REDIRECT_URI`, and required Google Health scopes in `.env`. Set `TOKEN_ENCRYPTION_KEY` to old deployment value before reading legacy encrypted tokens. `composer run dev` starts web server, queue listener, log viewer, and Vite.

Useful checks:

```bash
php artisan test
./vendor/bin/pint --test
npm run build
php artisan module:list
```

## Docker

Copy and configure environment first. Never use example database password in production.

```bash
cp .env.example .env
docker compose build
docker compose up -d
docker compose exec app php artisan migrate --force
docker compose ps
```

App binds to `127.0.0.1:3000`. Compose runs PostgreSQL, FrankenPHP app, queue worker, and scheduler. Route public traffic through existing Tailscale Serve or reverse proxy. Health endpoint: `/up`.

## Existing database cutover

Warning: database contains irreplaceable health history. Do not run `migrate:fresh`, reset migrations, or delete the PostgreSQL volume.

1. Stop old scheduler and writes.
2. Take verified PostgreSQL backup.
3. Preserve old `TOKEN_ENCRYPTION_KEY`, `SESSION_SECRET`, OAuth credentials, and callback URL.
4. Point Laravel at copied database first. Run `php artisan migrate --pretend` and inspect SQL.
5. Run additive migrations with `php artisan migrate --force`.
6. Verify bound `healthUserId`, token decryption, dashboard totals, scoring fixtures, and one controlled sync.
7. Switch traffic. Keep old image and backup available for rollback.

The LifeStats baseline migration creates only missing tables. Its rollback intentionally drops nothing. New schema changes must remain additive until parity and rollback window finish.

## Runtime operations

```bash
php artisan queue:work --tries=3 --timeout=900
php artisan schedule:work
php artisan route:list
php artisan migrate:status
```

OAuth session protects dashboard routes. API-style requests receive `401 {"error":"NOT_AUTHENTICATED"}`. Browser requests redirect to `/login`.

See [SCORING.md](SCORING.md) for model contract and safety limits.
