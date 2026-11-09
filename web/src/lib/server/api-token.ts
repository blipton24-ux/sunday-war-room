import "server-only";

import { SignJWT } from "jose";

import { env } from "./env";

/**
 * The short-lived token the web server attaches when it calls FastAPI (ADR-036).
 * Must match what api/app/auth/tokens.py verifies: HS256, iss "swr-web", aud "swr-api",
 * numeric `sub` (users.id). Never sent to the browser.
 */
export const API_TOKEN_TTL_SECONDS = 15 * 60;

export async function mintApiToken(userId: string | number): Promise<string> {
  const sub = String(userId);
  if (!/^\d+$/.test(sub)) throw new Error("API tokens carry a numeric user id");
  return new SignJWT({})
    .setProtectedHeader({ alg: "HS256", typ: "JWT" })
    .setSubject(sub)
    .setIssuer("swr-web")
    .setAudience("swr-api")
    .setIssuedAt()
    .setExpirationTime(`${API_TOKEN_TTL_SECONDS}s`)
    .sign(new TextEncoder().encode(env.apiJwtSecret));
}
