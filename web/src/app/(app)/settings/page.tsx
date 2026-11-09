"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

import { TitleRow } from "@/components/screen";
import { ConfirmDialog } from "@/components/ui/menu";
import { Card, ScreenSkeleton, Section, SecondaryButton } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";
import type { Schemas } from "@/lib/api/client";
import {
  useDeleteAccount,
  useLeagues,
  useMe,
  useSetMyTeam,
  useTeams,
  useUnfollowLeague,
} from "@/lib/api/queries";
import { authClient } from "@/lib/auth-client";
import { cn } from "@/lib/cn";
import { timeAgo } from "@/lib/format";

export default function SettingsPage() {
  const me = useMe();
  const leagues = useLeagues();
  const router = useRouter();
  const deleteAccount = useDeleteAccount();
  const toast = useToast();

  if (me.isLoading || leagues.isLoading) return <ScreenSkeleton />;

  async function signOut() {
    await authClient.signOut();
    router.replace("/sign-in");
    router.refresh();
  }

  return (
    <>
      <TitleRow title="Settings" />

      <Section title="Account">
        <Card className="flex flex-col gap-1">
          <span className="font-semibold">{me.data?.name || me.data?.email}</span>
          {me.data?.name && <span className="text-sm text-ink-lo">{me.data.email}</span>}
        </Card>
      </Section>

      <Section title="Connected platforms">
        <Card className="flex items-center justify-between gap-3">
          <div>
            <div className="font-semibold">Sleeper</div>
            <div className="text-sm text-ink-lo">
              {me.data?.sleeper_username ? `@${me.data.sleeper_username}` : "Not connected"}
            </div>
          </div>
          <Link href="/onboarding" className="text-sm font-semibold text-accent">
            {me.data?.sleeper_username ? "Add leagues" : "Connect"}
          </Link>
        </Card>
      </Section>

      <Section title="Leagues">
        <div className="flex flex-col gap-2">
          {(leagues.data ?? []).map((l) => (
            <LeagueSettings key={l.id} league={l} />
          ))}
        </div>
      </Section>

      <Section title="Theme">
        <ThemePicker />
      </Section>

      <Section title="Session">
        <div className="flex flex-col gap-2">
          <SecondaryButton className="w-full" onClick={signOut}>
            Sign out
          </SecondaryButton>
          <ConfirmDialog
            title="Delete your account?"
            description="This removes your account, your connected Sleeper username and the leagues you follow from Sunday War Room. Your Sleeper leagues themselves are not touched. This can't be undone."
            confirmLabel="Delete account"
            busy={deleteAccount.isPending}
            onConfirm={() =>
              deleteAccount.mutate(undefined, {
                onSuccess: async () => {
                  await authClient.signOut().catch(() => {});
                  router.replace("/sign-in");
                  router.refresh();
                },
                onError: () => toast("Couldn't delete the account. Try again."),
              })
            }
            trigger={
              <button className="min-h-11 rounded-[14px] px-4 text-sm font-semibold text-bad hover:bg-bad/10">
                Delete account
              </button>
            }
          />
        </div>
      </Section>
    </>
  );
}

function LeagueSettings({ league }: { league: Schemas["LeagueOut"] }) {
  const teams = useTeams(league.id);
  const setTeam = useSetMyTeam();
  const unfollow = useUnfollowLeague();
  const toast = useToast();
  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate font-semibold">{league.name}</div>
          <div className="text-xs text-ink-lo">
            {league.season} · synced {timeAgo(league.last_synced_at)}
          </div>
        </div>
        <ConfirmDialog
          title={`Unfollow ${league.name}?`}
          description="It disappears from your war room. You can follow it again from Add leagues."
          confirmLabel="Unfollow"
          busy={unfollow.isPending}
          onConfirm={() => unfollow.mutate(league.id, { onSuccess: () => toast("League removed") })}
          trigger={<button className="shrink-0 text-xs font-semibold text-ink-lo hover:text-bad">Unfollow</button>}
        />
      </div>
      <label className="mt-3 block text-xs font-semibold text-sea" htmlFor={`team-${league.id}`}>
        My team
      </label>
      <select
        id={`team-${league.id}`}
        value={league.my_team_id ?? ""}
        disabled={!teams.data || setTeam.isPending}
        onChange={(e) =>
          setTeam.mutate(
            { leagueId: league.id, teamId: Number(e.target.value) },
            { onSuccess: () => toast("Team saved") },
          )
        }
        className="mt-1 min-h-11 w-full rounded-xl bg-overlay px-3 text-sm outline-none"
      >
        <option value="" disabled>
          {teams.data ? "Choose your team" : "Loading teams…"}
        </option>
        {teams.data?.map((t) => (
          <option key={t.id} value={t.id}>
            {t.name}
            {t.owner_name ? ` (${t.owner_name})` : ""}
          </option>
        ))}
      </select>
    </Card>
  );
}

function ThemePicker() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const options = [
    ["dark", "Dark"],
    ["light", "Light"],
    ["system", "Match my phone"],
  ] as const;
  return (
    <div className="inline-flex gap-1 rounded-full bg-raised p-1" role="radiogroup" aria-label="Theme">
      {options.map(([value, label]) => (
        <button
          key={value}
          role="radio"
          aria-checked={mounted && theme === value}
          onClick={() => setTheme(value)}
          className={cn(
            "min-h-10 rounded-full px-3.5 text-sm font-semibold text-ink-lo",
            mounted && theme === value && "bg-high text-ink",
          )}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
