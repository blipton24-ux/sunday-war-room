"use client";

import { LeagueProvider } from "@/components/league-context";

import { Header } from "./header";
import { BottomNav, PillNav } from "./nav";
import { ReconnectBanner } from "./reconnect-banner";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <LeagueProvider>
      <Header />
      <PillNav />
      <ReconnectBanner />
      <main className="mx-auto flex max-w-5xl flex-col gap-4 px-4 pb-28 pt-3.5 sm:pb-10">
        {children}
      </main>
      <BottomNav />
    </LeagueProvider>
  );
}
