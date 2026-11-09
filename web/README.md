# web: Sunday War Room front end

Next.js app (built in P1 step 11). What exists so far is the **typed API client**
([ADR-014](../docs/Decisions/ADR-014-API-REST-OpenAPI.md)).

## The API client
```
FastAPI (Python types) ──▶ api/openapi.json ──▶ src/lib/api/schema.d.ts ──▶ screens
```
| Command | What it does |
|---|---|
| `npm run generate:api` | Regenerates `src/lib/api/schema.d.ts` from `../api/openapi.json` |
| `npm run check:api` | Fails if the committed file is stale (CI runs this) |
| `npm run typecheck` | `tsc --noEmit`: a renamed or removed backend field becomes a build error here |
| `npm test` | Vitest: client behavior (auth header, error handling) |

```ts
import { createApiClient, unwrap } from "@/lib/api/client";

const api = createApiClient({ baseUrl: process.env.NEXT_PUBLIC_API_URL!, getToken });
const matchup = await unwrap(
  api.GET("/api/v1/leagues/{league_id}/matchup", {
    params: { path: { league_id: 7 }, query: { week: 9 } },
  }),
);
```
`unwrap` returns the data or throws an `ApiError` carrying the API's stable `code`
(`league_not_found`, `rate_limited`, ...). Never edit `schema.d.ts` by hand.

## Windows note
Windows Smart App Control can refuse unsigned native files. `rollup`'s native build is blocked
on this machine, so `package.json` swaps in Rollup's WebAssembly build via `overrides`.
See [Improvement Backlog P-02](../docs/Build-Plan/Improvement-Backlog.md).

Related: [API](../api/README.md) · [OpenAPI and the typed client](../docs/Concepts/OpenAPI-Typed-Client.md)
