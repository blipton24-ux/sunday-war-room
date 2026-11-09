import { redirect } from "next/navigation";

import { AppShell } from "@/components/shell/app-shell";
import { unwrap } from "@/lib/api/client";
import { serverApi } from "@/lib/server/session";

// Per-user pages: never pre-rendered at build time.
export const dynamic = "force-dynamic";

/**
 * Everything behind sign-in. Checked on the server before any screen renders:
 * no session -> /sign-in; no league yet -> /onboarding.
 */
export default async function SignedInLayout({ children }: { children: React.ReactNode }) {
  const api = await serverApi(); // redirects to /sign-in when signed out
  const me = await unwrap(api.GET("/api/v1/me"));
  if (me.memberships.length === 0) redirect("/onboarding");
  return <AppShell>{children}</AppShell>;
}
