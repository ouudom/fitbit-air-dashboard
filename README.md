# Fitbit Air Dashboard

Personal local dashboard for Fitbit activity data through the Google Health API.

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

Drizzle owns the schema in `drizzle/schema.ts` and migrations in `drizzle/migrations/`. Existing SQLite data is not imported.

## Commands

- `npm run dev` — Next.js development server
- `npm run build` — production build
- `npm run db:generate` — generate a migration from schema changes
- `npm run db:migrate` — apply migrations
- `npm run db:studio` — open Drizzle Studio
