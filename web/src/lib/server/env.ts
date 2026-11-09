import "server-only";

import { assertNotDevSecret, parseLimit } from "./policy";

/**
 * Server environment variables, read in one place. `.env.example` (repo root) documents them.
 * Read lazily (getters): `next build` loads server modules without production secrets, so
 * a missing required variable fails loudly at first real use, never at build time and never
 * by silently defaulting in production.
 */
const isProduction = process.env.NODE_ENV === "production";

function required(name: string, devDefault?: string): string {
  const value = process.env[name];
  if (value) return value;
  if (!isProduction && devDefault !== undefined) return devDefault;
  throw new Error(`Missing required environment variable ${name}`);
}

function optional(name: string): string | undefined {
  return process.env[name] || undefined;
}

export const env = {
  get isProduction() {
    return isProduction;
  },
  /** Public URL of the web app, e.g. http://localhost:3000 */
  get appUrl() {
    return required("BETTER_AUTH_URL", "http://localhost:3000");
  },
  get authSecret() {
    const value = required("BETTER_AUTH_SECRET", "dev-only-better-auth-secret-change-me-0123456789");
    assertNotDevSecret("BETTER_AUTH_SECRET", value, env.appUrl, isProduction);
    return value;
  },
  /** Plain postgres:// URL for Better Auth (the API uses its own asyncpg URL). */
  get authDatabaseUrl() {
    return required("AUTH_DATABASE_URL", "postgres://swr:swr@localhost:5432/swr");
  },
  /** Shared with FastAPI: signs the short-lived API token (ADR-036). */
  get apiJwtSecret() {
    const value = required("API_JWT_SECRET", "dev-only-secret-change-me-0123456789abcdef");
    assertNotDevSecret("API_JWT_SECRET", value, env.appUrl, isProduction);
    return value;
  },
  /** Where the Next.js server reaches FastAPI (internal network in production). */
  get apiInternalUrl() {
    return required("API_INTERNAL_URL", "http://localhost:8000");
  },
  /** Sign-in link requests allowed per minute from one address (brute-force protection). */
  get magicLinkRateLimit() {
    return parseLimit(process.env.MAGIC_LINK_RATE_LIMIT_MAX, 5);
  },
  get googleClientId() {
    return optional("GOOGLE_CLIENT_ID");
  },
  get googleClientSecret() {
    return optional("GOOGLE_CLIENT_SECRET");
  },
  get resendApiKey() {
    return optional("RESEND_API_KEY");
  },
  get emailFrom() {
    return optional("EMAIL_FROM") ?? "Sunday War Room <signin@example.com>";
  },
};

/** Google sign-in shows only when both credentials are configured. */
export function googleEnabled(): boolean {
  return Boolean(env.googleClientId && env.googleClientSecret);
}
