/**
 * Typed API client (ADR-014). The types come from the generated `schema.d.ts`, so a backend
 * rename is a TypeScript error in every screen that uses the old name.
 *
 *   const api = createApiClient({ baseUrl, getToken });
 *   const matchup = await unwrap(
 *     api.GET("/api/v1/leagues/{league_id}/matchup", {
 *       params: { path: { league_id: 7 }, query: { week: 9 } },
 *     }),
 *   );
 *   matchup.outlook?.win_probability; // number, fully typed
 */
import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

export type Schemas = components["schemas"];
export type ApiClient = ReturnType<typeof createApiClient>;

export interface ApiClientOptions {
  /** Where the FastAPI server lives, e.g. http://localhost:8000 */
  baseUrl: string;
  /** The signed-in user's API token (ADR-017), or null when signed out. */
  getToken?: () => string | null | Promise<string | null>;
  /** Override fetch (tests, or Next.js server-side caching options). */
  fetch?: (request: Request) => Promise<Response>;
}

export function createApiClient(options: ApiClientOptions) {
  const client = createClient<paths>({
    baseUrl: options.baseUrl,
    ...(options.fetch ? { fetch: options.fetch } : {}),
  });
  client.use({
    async onRequest({ request }) {
      const token = await options.getToken?.();
      if (token) request.headers.set("Authorization", `Bearer ${token}`);
      return request;
    },
  });
  return client;
}

/** An error response from the API: `{ detail, code }` plus the HTTP status. */
export class ApiError extends Error {
  readonly status: number;
  /** Stable machine-readable code, e.g. "league_not_found" or "rate_limited". */
  readonly code: string;

  constructor(status: number, code: string, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export function isApiError(error: unknown, code?: string): error is ApiError {
  return error instanceof ApiError && (code === undefined || error.code === code);
}

interface Result<D> {
  data?: D;
  error?: Schemas["ErrorOut"];
  response: Response;
}

/** Return the data of a call, or throw an `ApiError` carrying the API's `code`. */
export async function unwrap<D>(call: Promise<Result<D>>): Promise<D> {
  const result = await call;
  if (result.error !== undefined) {
    // The API always sends {detail, code}. Anything else (a proxy's HTML 502, a network
    // layer error) still becomes an ApiError so callers have one thing to catch.
    const body: unknown = result.error;
    const shaped =
      typeof body === "object" && body !== null && "code" in body && "detail" in body;
    throw new ApiError(
      result.response.status,
      shaped ? String((body as Schemas["ErrorOut"]).code) : "http_error",
      shaped ? String((body as Schemas["ErrorOut"]).detail) : `HTTP ${result.response.status}`,
    );
  }
  return result.data as D;
}
