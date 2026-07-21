# LifeStats

Personal health dashboard. Laravel serves Inertia pages and owns persistence, OAuth, sync, scoring, and write operations. React renders dashboard UI. PostgreSQL schema remains compatible with the earlier deployment.

## Stack

- PHP 8.5
- Laravel 13
- Inertia 3
- React 19 + TypeScript
- Vite 8
- PostgreSQL 17
- FrankenPHP production runtime

## Modular structure

```text
app/
├── Domain/
│   ├── Analytics/   # queries, wellness scoring, journal insights
│   ├── Coach/       # provider boundary, context, response streaming
│   └── Health/      # Google API, OAuth, crypto, sync, write operations
├── Http/
│   ├── Controllers/ # thin Inertia and mutation endpoints
│   └── Middleware/  # Inertia props and health-session gate
├── Jobs/            # queued health synchronization
└── Models/          # legacy-schema Eloquent mappings
resources/js/
├── components/      # reusable UI and chart primitives
├── layouts/         # application shell
├── pages/           # route-level Inertia pages
└── types/           # shared TypeScript contracts
```

Domain code must not depend on React or controllers. Controllers validate input and delegate work. External services sit behind domain clients/contracts. Legacy models keep millisecond timestamps, string IDs, and existing column names.

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
