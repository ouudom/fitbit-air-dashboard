# Fitbit Air Dashboard

Personal local dashboard for Fitbit activity data through the Google Health API.

Stack: Node.js API, PostgreSQL, Next.js 16 App Router, React 19, TypeScript.

## Run

Create a PostgreSQL database and user, then configure `.env`:

```bash
createdb fitbit_air
cp .env.example .env
# fill GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
```

Start the API and frontend in separate terminals:

```bash
npm install
npm start

cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The API runs at http://localhost:8080. Add
`http://localhost:8080/oauth/callback` as an authorized redirect URI in Google Cloud.

The API applies `db/migrations/001_initial.sql` at startup. Existing SQLite data is not imported.

## Commands

- `npm run dev` — API watch mode
- `npm run sync` — command-line Fitbit sync
- `npm run frontend:dev` — Next.js development server
- `npm run frontend:build` — production frontend build
