"use client";

/**
 * Which league and week the screens are showing. The league choice is remembered on this
 * device; the week starts at the league's current week whenever the league changes.
 */
import { createContext, useContext, useEffect, useMemo, useState } from "react";

import type { Schemas } from "@/lib/api/client";
import { useLeagues } from "@/lib/api/queries";

interface LeagueState {
  leagues: Schemas["LeagueOut"][];
  league: Schemas["LeagueOut"] | null;
  leagueId: number | null;
  week: number | null;
  setLeagueId: (id: number) => void;
  setWeek: (week: number) => void;
  isLoading: boolean;
}

const LeagueContext = createContext<LeagueState | null>(null);
const STORAGE_KEY = "swr.leagueId";

export function LeagueProvider({ children }: { children: React.ReactNode }) {
  const { data: leagues = [], isLoading } = useLeagues();
  const [chosen, setChosen] = useState<number | null>(null);
  const [weekByLeague, setWeekByLeague] = useState<Record<number, number>>({});

  useEffect(() => {
    const saved = Number(window.localStorage.getItem(STORAGE_KEY));
    if (saved) setChosen(saved);
  }, []);

  const league = leagues.find((l) => l.id === chosen) ?? leagues[0] ?? null;
  const week = league ? (weekByLeague[league.id] ?? league.current_week ?? null) : null;

  const value = useMemo<LeagueState>(
    () => ({
      leagues,
      league,
      leagueId: league?.id ?? null,
      week,
      isLoading,
      setLeagueId: (id) => {
        setChosen(id);
        window.localStorage.setItem(STORAGE_KEY, String(id));
      },
      setWeek: (w) => {
        if (league) setWeekByLeague((s) => ({ ...s, [league.id]: Math.min(18, Math.max(1, w)) }));
      },
    }),
    [leagues, league, week, isLoading],
  );
  return <LeagueContext.Provider value={value}>{children}</LeagueContext.Provider>;
}

export function useLeague(): LeagueState {
  const ctx = useContext(LeagueContext);
  if (!ctx) throw new Error("useLeague must be used inside <LeagueProvider>");
  return ctx;
}
