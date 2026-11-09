// Better Auth's endpoints: sign in with Google, magic links, session, sign out (ADR-035).
import { toNextJsHandler } from "better-auth/next-js";

import { getAuth } from "@/lib/server/auth";

export const dynamic = "force-dynamic";

export function GET(request: Request) {
  return toNextJsHandler(getAuth()).GET(request);
}

export function POST(request: Request) {
  return toNextJsHandler(getAuth()).POST(request);
}
