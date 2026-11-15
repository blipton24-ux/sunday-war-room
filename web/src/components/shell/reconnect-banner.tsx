"use client";

import { KeyRound } from "lucide-react";
import Link from "next/link";

import { useMe } from "@/lib/api/queries";
import { espnConnectPath } from "@/lib/espn";

/**
 * Shown on every signed-in screen while the user's ESPN cookies are refused (ADR-051). Their
 * ESPN leagues stay followed but pause until they reconnect; nothing is shown from anyone else's
 * login.
 */
export function ReconnectBanner() {
  const me = useMe();
  const expired = me.data?.platforms.some(
    (p) => p.platform === "espn" && p.status === "needs_reconnect",
  );
  if (!expired) return null;
  return (
    <div
      role="status"
      className="mx-auto mt-2 flex max-w-5xl items-center gap-3 rounded-[14px] bg-warn/15 px-4 py-2.5 text-sm text-warn"
    >
      <KeyRound className="size-4 shrink-0" aria-hidden />
      <span className="min-w-0 flex-1">
        Your ESPN sign-in expired, so your ESPN leagues have paused.
      </span>
      <Link href={espnConnectPath()} className="shrink-0 font-extrabold underline">
        Reconnect
      </Link>
    </div>
  );
}
