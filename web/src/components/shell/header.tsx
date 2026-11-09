"use client";

import { useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronLeft, ChevronRight, Moon, RefreshCw, Sun } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

import { useLeague } from "@/components/league-context";
import { Menu, MenuContent, MenuItem, MenuSeparator, MenuTrigger } from "@/components/ui/menu";
import { useToast } from "@/components/ui/toast";
import { isApiError } from "@/lib/api/client";
import { isFinished, useJob, useRefreshLeague } from "@/lib/api/queries";
import { authClient } from "@/lib/auth-client";
import { cn } from "@/lib/cn";
import { timeAgo } from "@/lib/format";

import { Logo, Wordmark } from "./logo";

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-accent/20 bg-base pt-[env(safe-area-inset-top)]">
      <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-2.5">
        <Link href="/" aria-label="Home" className="shrink-0">
          <Logo size={40} className="rounded-xl" />
        </Link>
        <span className="hidden md:block">
          <Wordmark />
        </span>
        <span className="hidden h-7 w-px bg-line-strong md:block" />
        <LeagueMenu />
        <span className="flex-1" />
        <WeekStepper />
        <RefreshButton />
        <ThemeToggle />
      </div>
    </header>
  );
}

function useNow(intervalMs = 30_000): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}

function LeagueMenu() {
  const { leagues, league, setLeagueId, isLoading } = useLeague();
  const router = useRouter();
  const now = useNow();
  const syncing = league?.sync_status === "queued" || league?.sync_status === "running";
  const stale =
    !league?.last_synced_at || now.getTime() - new Date(league.last_synced_at).getTime() > 2 * 3600_000;

  async function signOut() {
    await authClient.signOut();
    router.replace("/sign-in");
    router.refresh();
  }

  if (isLoading && !league) {
    // Neutral placeholder: never flash "No league · synced never" while leagues load.
    return <span aria-hidden className="h-9 w-32 animate-pulse rounded-xl bg-raised" />;
  }

  return (
    <Menu>
      <MenuTrigger className="flex min-w-0 flex-col items-start rounded-xl px-2 py-1 text-left leading-tight hover:bg-raised">
        <b className="flex max-w-[11rem] items-center gap-1 truncate text-[0.95rem] font-bold sm:max-w-xs">
          <span className="truncate">{league?.name ?? "No league"}</span>
          <ChevronDown className="size-4 shrink-0 text-ink-lo" aria-hidden />
        </b>
        <small className="flex items-center gap-1.5 text-[0.72rem] text-ink-lo">
          <i
            className={cn(
              "size-1.5 shrink-0 rounded-full",
              syncing ? "animate-live bg-accent" : stale ? "bg-warn" : "bg-good",
            )}
          />
          {syncing ? "syncing…" : `synced ${timeAgo(league?.last_synced_at, now)}`}
        </small>
      </MenuTrigger>
      <MenuContent>
        {leagues.map((l) => (
          <MenuItem key={l.id} active={l.id === league?.id} onSelect={() => setLeagueId(l.id)}>
            <span className="truncate">{l.name}</span>
            {l.id === league?.id && <span aria-hidden>●</span>}
          </MenuItem>
        ))}
        <MenuSeparator />
        <MenuItem className="text-accent" onSelect={() => router.push("/onboarding")}>
          + Connect a league
        </MenuItem>
        <MenuItem onSelect={() => router.push("/settings")}>Settings</MenuItem>
        <MenuItem onSelect={signOut}>Sign out</MenuItem>
      </MenuContent>
    </Menu>
  );
}

function WeekStepper() {
  const { week, setWeek, league } = useLeague();
  if (week == null) return null;
  const current = league?.current_week;
  return (
    <div className="flex items-center rounded-full bg-raised p-[3px]">
      <button
        aria-label="Previous week"
        disabled={week <= 1}
        onClick={() => setWeek(week - 1)}
        className="grid size-8 place-items-center rounded-full text-ink-lo hover:bg-overlay hover:text-ink disabled:opacity-30"
      >
        <ChevronLeft className="size-4" />
      </button>
      <button
        onClick={() => current && setWeek(current)}
        title={current && week !== current ? `Back to week ${current}` : undefined}
        className={cn("nums px-1 text-[0.8rem] font-bold", current && week !== current && "text-accent")}
      >
        Wk {week}
      </button>
      <button
        aria-label="Next week"
        disabled={week >= 18}
        onClick={() => setWeek(week + 1)}
        className="grid size-8 place-items-center rounded-full text-ink-lo hover:bg-overlay hover:text-ink disabled:opacity-30"
      >
        <ChevronRight className="size-4" />
      </button>
    </div>
  );
}

function RefreshButton() {
  const { leagueId } = useLeague();
  const refresh = useRefreshLeague();
  const [jobId, setJobId] = useState<string | null>(null);
  const job = useJob(jobId);
  const qc = useQueryClient();
  const toast = useToast();

  useEffect(() => {
    if (!jobId || !isFinished(job.data)) return;
    if (job.data?.status === "done") {
      toast("League updated");
      void qc.invalidateQueries();
    } else {
      toast("Sync failed. Try again in a minute.");
    }
    setJobId(null);
  }, [job.data, jobId, qc, toast]);

  const busy = refresh.isPending || jobId != null;
  return (
    <button
      aria-label="Refresh league"
      disabled={busy || leagueId == null}
      onClick={() =>
        leagueId != null &&
        refresh.mutate(leagueId, {
          onSuccess: (r) => {
            setJobId(r.job_id);
            toast("Syncing in the background…");
            void qc.invalidateQueries({ queryKey: ["leagues"] });
          },
          onError: (e) => toast(isApiError(e) ? e.message : "Couldn't start a sync"),
        })
      }
      className="grid size-11 shrink-0 place-items-center rounded-full bg-raised text-ink-mid hover:bg-overlay hover:text-ink sm:size-9"
    >
      <RefreshCw className={cn("size-[18px]", busy && "animate-spin text-accent")} />
    </button>
  );
}

function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const dark = resolvedTheme !== "light";
  return (
    <button
      aria-label={mounted ? `Switch to ${dark ? "light" : "dark"} theme` : "Toggle theme"}
      onClick={() => setTheme(dark ? "light" : "dark")}
      className="grid size-11 shrink-0 place-items-center rounded-full bg-raised text-ink-mid hover:bg-overlay hover:text-ink sm:size-9"
    >
      {mounted && !dark ? <Sun className="size-[18px]" /> : <Moon className="size-[18px]" />}
    </button>
  );
}
