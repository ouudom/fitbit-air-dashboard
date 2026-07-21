# LifeStats

Private, Bevel-inspired web health coach using Fitbit data from Google Health API. Includes explained Recovery, Sleep, Strain, physiological Stress, Energy, Timeline, Trends, Journal, Strength, Nutrition, Health Monitor, and evidence-grounded AI coach.

Stack: Next.js 16 App Router, React 19, TypeScript, Drizzle ORM, PostgreSQL.

## Run

Create a PostgreSQL database and user, then configure `.env`:

```bash
createdb fitbit_air
cp .env.example .env
# fill GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
```

Install dependencies, apply Drizzle migrations, and start Next.js:

```bash
npm install
npm run db:migrate
npm run dev
```

Open http://localhost:3000. Add
`http://localhost:3000/api/auth/callback` as an authorized redirect URI in Google Cloud.

Generate unique `SESSION_SECRET`, `TOKEN_ENCRYPTION_KEY`, `CRON_SECRET`, and optionally configure the AI coach with `LLM_API_KEY`, `LLM_MODEL`, and `LLM_BASE_URL`. The provider must expose an OpenAI-compatible Responses API at `{LLM_BASE_URL}/responses` and accept Bearer authentication. `OPENAI_API_KEY` and `OPENAI_MODEL` remain legacy fallbacks. Changed Google scopes require reconnecting Fitbit and granting consent again.

Drizzle owns the schema in `drizzle/schema.ts` and migrations in `drizzle/migrations/`. Existing SQLite data is not imported.

The expanded OAuth configuration requests read access for activity, health measurements, sleep, ECG, irregular-rhythm notifications, nutrition, location, profile, and settings. After changing scopes, connect Fitbit again so Google shows the new consent screen. The API stores supported records in `health_records`; unavailable device metrics are recorded as sync errors without stopping other metrics.

Google's current data-type reference lists activity, sleep, heart rate, HRV, resting heart rate, oxygen saturation, respiratory rate, temperature, VO2 max, ECG, nutrition, weight, and related data types. See the [Google Health API data types](https://developers.google.com/health/data-types) and [scope reference](https://developers.google.com/health/scopes).

## Commands

- `npm run dev` — Next.js development server
- `npm run build` — production build
- `npm run db:generate` — generate a migration from schema changes
- `npm run db:migrate` — apply migrations
- `npm run db:studio` — open Drizzle Studio

## Home server

Set `POSTGRES_PASSWORD`. Use HTTPS Tailscale hostname for `NEXT_PUBLIC_APP_URL` and `REDIRECT_URI`. Run `docker compose up -d --build`. App binds only to loopback; publish through Tailscale Serve. Scheduler performs hourly sync. Back up `fitbit_air_db` Docker volume.

Scores are wellness estimates, not medical guidance. See `SCORING.md` for formula versioning, baseline gates, and confidence rules.
