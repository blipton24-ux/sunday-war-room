# web: Sunday War Room front end

Next.js 16 (App Router) + React 19 + TypeScript, Tailwind CSS 4, TanStack Query, Better Auth.
Look and feel: [mockup v3](../mockups/p1-screens-v3.html) and [UI Screens](../docs/Specs/UI-Screens.md).

## Run it locally
```bash
# from FFCC/: data services, then the API and worker (see api/README.md)
docker compose up -d db redis
cd api && .venv/Scripts/uvicorn app.main:app --port 8000     # terminal 1
cd api && .venv/Scripts/arq app.worker.WorkerSettings        # terminal 2

# from FFCC/web/
npm install
npm run dev                                                   # http://localhost:3000
```
No `.env.local` is needed for local development: every server setting has a development
default (see `src/lib/server/env.ts` and the root `.env.example`). Without `RESEND_API_KEY`,
**"Email me a link" prints the sign-in link in this terminal**. "Sign in with Google" appears
once `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set.

## How the pieces connect
```
browser ──► Next.js (this app) ──► FastAPI
            /api/auth/*   Better Auth: sign-in, sessions (ADR-035)
            /api/v1/*     pass-through: checks the session, adds a 15-minute API token (ADR-036)
            /_next/image  resized, cached ESPN photos (ADR-037)
```
The browser never talks to FastAPI and never holds the API token.

| Path | What |
|---|---|
| `src/app/(app)/` | Signed-in screens: Home, Lineup, Matchup, Accuracy, Settings, coming-soon tabs |
| `src/app/sign-in/`, `src/app/onboarding/` | Sign-in, and Sleeper → leagues → my team |
| `src/app/api/` | Better Auth route and the `/api/v1` pass-through |
| `src/lib/server/` | Server-only: env, auth, API token, session helpers |
| `src/lib/api/` | Generated types (`schema.d.ts`), typed client, data hooks |
| `src/lib/*.ts` | Pure helpers (formatting, insights, positions, team colors), unit tested |
| `src/components/` | Shell (header, tabs), player rows, matchup and lineup pieces, UI primitives |

## Commands
| Command | What it does |
|---|---|
| `npm run dev` / `npm run build` | Develop / production build (needs no secrets at build time) |
| `npm run typecheck` | `tsc --noEmit`: a renamed backend field is a build error here |
| `npm test` | Vitest: client, pass-through URL safety, token claims, screen helpers |
| `npm run generate:api` / `npm run check:api` | Regenerate / verify `src/lib/api/schema.d.ts` from `../api/openapi.json` |
| `npm run auth:schema` | Print the tables Better Auth expects (point `AUTH_SCHEMA_DATABASE_URL` at an empty DB); Alembic's migration must match |

```ts
import { createApiClient, unwrap } from "@/lib/api/client";

const matchup = await unwrap(
  api.GET("/api/v1/leagues/{league_id}/matchup", {
    params: { path: { league_id: 7 }, query: { week: 9 } },
  }),
);
```
`unwrap` returns the data or throws an `ApiError` with the API's stable `code`
(`league_not_found`, `team_not_chosen`, `rate_limited`, …). Never edit `schema.d.ts` by hand.

Related: [API](../api/README.md) · [OpenAPI and the typed client](../docs/Concepts/OpenAPI-Typed-Client.md) · [Improvement Backlog](../docs/Build-Plan/Improvement-Backlog.md)
