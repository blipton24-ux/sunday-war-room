/**
 * Pass-through from the browser to FastAPI (ADR-036).
 *
 * The browser only ever talks to this origin. Here the session cookie is checked, a
 * 15-minute API token is minted, and the request is forwarded to FastAPI unchanged. The
 * response (status and `{detail, code}` errors included) goes back as it came.
 */
import { randomUUID } from "node:crypto";

import type { NextRequest } from "next/server";

import { mintApiToken } from "@/lib/server/api-token";
import { getAuth } from "@/lib/server/auth";
import { env } from "@/lib/server/env";
import { BadProxyPath, upstreamUrl } from "@/lib/server/upstream";

export const dynamic = "force-dynamic";

const FORWARD_RESPONSE_HEADERS = ["content-type", "x-request-id", "retry-after"];

function error(status: number, code: string, detail: string): Response {
  return Response.json({ detail, code }, { status });
}

async function forward(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  const session = await getAuth().api.getSession({ headers: request.headers });
  if (!session) return error(401, "unauthorized", "Not signed in");

  let url: URL;
  try {
    url = upstreamUrl((await context.params).path, request.nextUrl.search, env.apiInternalUrl);
  } catch (e) {
    if (e instanceof BadProxyPath) return error(400, "bad_path", "Invalid API path");
    throw e;
  }

  const requestId = request.headers.get("x-request-id") ?? randomUUID().slice(0, 16);
  const headers = new Headers({
    Authorization: `Bearer ${await mintApiToken(session.user.id)}`,
    Accept: "application/json",
    "x-request-id": requestId,
  });
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  const hasBody = !["GET", "HEAD"].includes(request.method);

  let upstream: Response;
  try {
    upstream = await fetch(url, {
      method: request.method,
      headers,
      body: hasBody ? await request.arrayBuffer() : undefined,
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.timeout(30_000),
    });
  } catch {
    return error(502, "upstream_unavailable", "The data service is unavailable. Try again shortly.");
  }

  const out = new Headers({ "cache-control": "no-store" });
  for (const name of FORWARD_RESPONSE_HEADERS) {
    const value = upstream.headers.get(name);
    if (value) out.set(name, value);
  }
  return new Response(upstream.status === 204 ? null : upstream.body, {
    status: upstream.status,
    headers: out,
  });
}

export { forward as DELETE, forward as GET, forward as PATCH, forward as POST, forward as PUT };
