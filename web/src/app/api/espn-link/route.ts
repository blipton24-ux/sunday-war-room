/**
 * "Email me a link to finish on a computer" (ADR-051).
 *
 * Copying the two ESPN cookies can't be done on a phone, so the connect screen offers to email the
 * signed-in user a link that opens the same step. The email goes only to the address on the
 * user's own session (never to one typed into a request), and at most 3 a minute per user, so
 * this can't be used to send mail to other people.
 */
import type { NextRequest } from "next/server";

import { createRateLimiter } from "@/lib/rate-limit";
import { espnConnectPath } from "@/lib/espn";
import { getAuth } from "@/lib/server/auth";
import { sendEspnLinkEmail } from "@/lib/server/email";
import { env } from "@/lib/server/env";

export const dynamic = "force-dynamic";

const limiter = createRateLimiter(3, 60_000);

function error(status: number, code: string, detail: string): Response {
  return Response.json({ detail, code }, { status });
}

export async function POST(request: NextRequest): Promise<Response> {
  const session = await getAuth().api.getSession({ headers: request.headers });
  if (!session) return error(401, "unauthorized", "Not signed in");
  const email = session.user.email;
  if (!email) return error(422, "no_email", "Your account has no email address to send to");
  if (!limiter.take(session.user.id)) {
    return error(429, "rate_limited", "Sent a moment ago. Check your inbox, or try again in a minute.");
  }
  try {
    await sendEspnLinkEmail(email, new URL(espnConnectPath(), env.appUrl).toString());
  } catch {
    return error(502, "email_failed", "Couldn't send the email. Try again shortly.");
  }
  return new Response(null, { status: 204 });
}
