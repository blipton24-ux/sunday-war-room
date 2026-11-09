import "server-only";

import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { cache } from "react";

import { createApiClient } from "@/lib/api/client";

import { mintApiToken } from "./api-token";
import { getAuth } from "./auth";
import { env } from "./env";

/** The signed-in session for this request, or null. Cached per request. */
export const getSession = cache(async () => {
  // Read the request first: it marks the page as per-request before any auth work happens.
  const requestHeaders = await headers();
  return getAuth().api.getSession({ headers: requestHeaders });
});

/** Use in server components and layouts that require sign-in. */
export async function requireSession() {
  const session = await getSession();
  if (!session) redirect("/sign-in");
  return session;
}

/**
 * Typed FastAPI client for server components, calling the API directly over the internal
 * network with this user's token (ADR-036).
 */
export async function serverApi() {
  const session = await requireSession();
  return createApiClient({
    baseUrl: env.apiInternalUrl,
    getToken: () => mintApiToken(session.user.id),
    fetch: (request) => fetch(request, { cache: "no-store" }),
  });
}
