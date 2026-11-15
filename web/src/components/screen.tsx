"use client";

import type { UseQueryResult } from "@tanstack/react-query";
import { CalendarClock, KeyRound, RefreshCw, UserRound } from "lucide-react";
import Link from "next/link";

import { useLeague } from "@/components/league-context";
import { EmptyState, ErrorState, ScreenSkeleton } from "@/components/ui/primitives";
import { isApiError } from "@/lib/api/client";
import { espnConnectPath } from "@/lib/espn";
import { platformName } from "@/lib/format";

export function TitleRow({ title, note }: { title: string; note?: React.ReactNode }) {
  return (
    <div className="mt-1 flex items-center justify-between gap-3">
      <h2 className="page-title">{title}</h2>
      {note && <small className="text-right text-[0.8rem] text-ink-lo">{note}</small>}
    </div>
  );
}

/**
 * Renders a screen's data, or the right designed state: loading skeleton, "choose your
 * team", "first sync running", or an error with retry (UI Screens: every screen has them).
 */
export function Gate<T>({
  query,
  noRoster,
  children,
}: {
  query: Pick<UseQueryResult<T>, "data" | "error" | "isLoading" | "refetch">;
  /** True when the data exists but no roster is stored for this week (a future week). */
  noRoster?: (data: T) => boolean;
  children: (data: T) => React.ReactNode;
}) {
  const { league, week, setWeek, isLoading: leaguesLoading } = useLeague();
  if (leaguesLoading || (query.isLoading && !query.data)) return <ScreenSkeleton />;
  if (league && league.last_synced_at == null) {
    return (
      <EmptyState icon={RefreshCw} title="Syncing your league">
        We&apos;re pulling {league.name} from {platformName(league.platform)}. This page fills in by
        itself in a moment.
      </EmptyState>
    );
  }
  if (query.error) {
    if (isApiError(query.error, "credentials_expired")) {
      return (
        <EmptyState
          icon={KeyRound}
          title="Reconnect ESPN"
          action={
            <Link
              href={espnConnectPath()}
              className="rounded-[14px] bg-accent px-4 py-3 font-extrabold text-on-accent"
            >
              Reconnect ESPN
            </Link>
          }
        >
          Your ESPN sign-in for {league?.name ?? "this league"} expired. ESPN signs you out when you
          log out or change your password. Copy your two cookies again to pick up where you left off.
        </EmptyState>
      );
    }
    if (isApiError(query.error, "team_not_chosen")) {
      return (
        <EmptyState
          icon={UserRound}
          title="Which team is yours?"
          action={
            <Link href="/settings" className="rounded-[14px] bg-accent px-4 py-3 font-extrabold text-on-accent">
              Choose my team
            </Link>
          }
        >
          Pick your team in {league?.name ?? "this league"} so we can show your lineup and matchup.
        </EmptyState>
      );
    }
    if (isApiError(query.error, "not_synced")) {
      return (
        <EmptyState icon={RefreshCw} title="Syncing your league">
          The first sync is still running. This page fills in by itself in a moment.
        </EmptyState>
      );
    }
    return (
      <ErrorState
        message={isApiError(query.error) ? query.error.message : "Couldn't load this screen."}
        onRetry={() => void query.refetch()}
      />
    );
  }
  if (query.data === undefined) return <ScreenSkeleton />;
  if (noRoster?.(query.data)) {
    const current = league?.current_week;
    return (
      <EmptyState
        icon={CalendarClock}
        title={`Week ${week} isn't here yet`}
        action={
          current && current !== week ? (
            <button onClick={() => setWeek(current)} className="font-semibold text-accent">
              Back to Week {current}
            </button>
          ) : undefined
        }
      >
        Lineups for a week appear once it becomes the current week in your league.
      </EmptyState>
    );
  }
  return <>{children(query.data)}</>;
}
