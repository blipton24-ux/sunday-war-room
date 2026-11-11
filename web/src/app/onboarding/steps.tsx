"use client";

import { Check, LoaderCircle } from "lucide-react";
import { useEffect, useState } from "react";

import { Card, PrimaryButton, SecondaryButton } from "@/components/ui/primitives";
import { isApiError } from "@/lib/api/client";
import { useFollowLeague, useJob, useSetMyTeam, useTeams } from "@/lib/api/queries";
import { cn } from "@/lib/cn";
import { isMyTeam } from "@/lib/espn";

import type { Followed, Offer } from "./types";

export function StepTitle({
  step,
  title,
  children,
}: {
  step: number;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div>
      <p className="eyebrow">Step {step} of 3</p>
      <h1 className="page-title">{title}</h1>
      {children && <p className="mt-2 text-sm text-ink-lo">{children}</p>}
    </div>
  );
}

const PLATFORM_NAMES = { sleeper: "Sleeper", espn: "ESPN" } as const;

// --------------------------------------------------------------------------- pick leagues
export function LeaguesStep({
  offer,
  onFollowed,
}: {
  offer: Offer;
  onFollowed: (followed: Followed[]) => void;
}) {
  const [picked, setPicked] = useState<Set<string>>(
    () => new Set(offer.leagues.map((l) => l.external_id)),
  );
  const follow = useFollowLeague();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const name = PLATFORM_NAMES[offer.platform];

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const results: Followed[] = [];
      for (const league of offer.leagues.filter((l) => picked.has(l.external_id))) {
        const r = await follow.mutateAsync({ platform: offer.platform, externalId: league.external_id });
        results.push({
          external: league,
          platform: offer.platform,
          leagueId: r.league.id,
          jobId: r.job_id,
          ownerId: offer.ownerId,
        });
      }
      onFollowed(results);
    } catch (e) {
      setError(isApiError(e) ? e.message : "Couldn't follow those leagues. Try again.");
      setBusy(false);
    }
  }

  if (offer.leagues.length === 0) {
    return (
      <>
        <StepTitle step={2} title="No leagues yet">
          {offer.label ? `${offer.label} has` : "That account has"} no {name} leagues for the{" "}
          {offer.season || "current"} season.
        </StepTitle>
        <SecondaryButton
          onClick={() => window.location.assign(`/onboarding?platform=${offer.platform}`)}
        >
          {offer.platform === "sleeper" ? "Try another username" : "Try again"}
        </SecondaryButton>
      </>
    );
  }

  return (
    <>
      <StepTitle step={2} title="Pick your leagues">
        Found {offer.leagues.length} league{offer.leagues.length > 1 ? "s" : ""}
        {offer.label ? (
          <>
            {" "}
            for <b className="text-ink">{offer.label}</b>
          </>
        ) : null}
        {offer.season ? ` in ${offer.season}` : ""}.
      </StepTitle>
      <div className="flex flex-col gap-2">
        {offer.leagues.map((l) => {
          const on = picked.has(l.external_id);
          return (
            <button
              key={l.external_id}
              type="button"
              aria-pressed={on}
              onClick={() =>
                setPicked((s) => {
                  const next = new Set(s);
                  if (on) next.delete(l.external_id);
                  else next.add(l.external_id);
                  return next;
                })
              }
              className={cn(
                "flex min-h-14 items-center gap-3 rounded-[1.1rem] bg-raised px-4 py-3 text-left",
                on && "accent-ring",
              )}
            >
              <span
                className={cn(
                  "grid size-6 shrink-0 place-items-center rounded-md border border-line-strong",
                  on && "border-accent bg-accent text-on-accent",
                )}
              >
                {on && <Check className="size-4" />}
              </span>
              <span className="min-w-0">
                <span className="block truncate font-semibold">{l.name}</span>
                <span className="text-xs text-ink-lo">
                  {l.total_teams ? `${l.total_teams} teams · ` : ""}
                  {l.season || ""}
                </span>
              </span>
            </button>
          );
        })}
      </div>
      <PrimaryButton disabled={busy || picked.size === 0} onClick={submit}>
        {busy ? "Starting…" : `Follow ${picked.size} league${picked.size === 1 ? "" : "s"}`}
      </PrimaryButton>
      {error && <p className="text-sm text-bad">{error}</p>}
    </>
  );
}

// --------------------------------------------------------------------------- pick my team
export function TeamsStep({ followed, onDone }: { followed: Followed[]; onDone: () => void }) {
  const [chosen, setChosen] = useState<Record<number, boolean>>({});
  const allChosen = followed.every((f) => chosen[f.leagueId]);
  return (
    <>
      <StepTitle step={3} title="Which team is yours?">
        We&apos;re syncing each league now. Confirm your team in each one.
      </StepTitle>
      <div className="flex flex-col gap-3">
        {followed.map((f) => (
          <LeagueTeamPicker
            key={f.leagueId}
            followed={f}
            onChosen={() => setChosen((c) => ({ ...c, [f.leagueId]: true }))}
          />
        ))}
      </div>
      <PrimaryButton disabled={!allChosen} onClick={onDone}>
        {allChosen ? "Go to my war room →" : "Pick a team in each league"}
      </PrimaryButton>
    </>
  );
}

function LeagueTeamPicker({ followed, onChosen }: { followed: Followed; onChosen: () => void }) {
  const job = useJob(followed.jobId);
  const synced = job.data?.status === "done";
  const teams = useTeams(synced ? followed.leagueId : null);
  const setTeam = useSetMyTeam();
  const [teamId, setTeamId] = useState<number | null>(null);
  const [saved, setSaved] = useState(false);
  const mine = { teamId: followed.external.team_id, ownerId: followed.ownerId };

  // Pre-select the team the platform says is the user's (ESPN: team id; Sleeper: owner id).
  useEffect(() => {
    if (teamId == null && teams.data) {
      const found = teams.data.find((t) => isMyTeam(t, mine));
      if (found) setTeamId(found.id);
    }
  }, [teams.data, mine.teamId, mine.ownerId, teamId]); // eslint-disable-line react-hooks/exhaustive-deps

  function save(id: number) {
    setTeamId(id);
    setTeam.mutate(
      { leagueId: followed.leagueId, teamId: id },
      {
        onSuccess: () => {
          setSaved(true);
          onChosen();
        },
      },
    );
  }

  return (
    <Card>
      <div className="flex items-center justify-between gap-2">
        <b className="truncate">{followed.external.name}</b>
        {job.data?.status === "failed" ? (
          <span className="text-xs text-bad">{syncFailure(job.data.error)}</span>
        ) : !synced ? (
          <span className="flex items-center gap-1.5 text-xs text-ink-lo">
            <LoaderCircle className="size-3.5 animate-spin" /> syncing…
          </span>
        ) : saved ? (
          <span className="flex items-center gap-1 text-xs text-good">
            <Check className="size-3.5" /> saved
          </span>
        ) : null}
      </div>
      {synced && teams.data && (
        <div className="mt-3 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
          {teams.data.map((t) => (
            <button
              key={t.id}
              onClick={() => save(t.id)}
              disabled={setTeam.isPending}
              className={cn(
                "flex min-h-11 items-center justify-between gap-2 rounded-xl bg-overlay px-3 py-2 text-left text-sm",
                teamId === t.id && "accent-soft text-accent",
              )}
            >
              <span className="min-w-0">
                <span className="block truncate font-semibold">{t.name}</span>
                <span className="block truncate text-[0.7rem] text-ink-lo">
                  {t.owner_name ?? "No manager"}
                  {isMyTeam(t, mine) ? " · you" : ""}
                </span>
              </span>
              <span className="nums text-xs text-ink-lo">
                {t.wins}-{t.losses}
                {t.ties ? `-${t.ties}` : ""}
              </span>
            </button>
          ))}
        </div>
      )}
      {synced && teamId != null && !saved && (
        <p className="mt-2 text-xs text-ink-lo">Tap your team to confirm.</p>
      )}
    </Card>
  );
}

/** A short reason a first sync failed, in the user's words. */
function syncFailure(error: string | null | undefined): string {
  if (error?.includes("CredentialsInvalid")) return "ESPN sign-in expired";
  if (error?.includes("AuthRequired")) return "league is private";
  if (error?.includes("UnsupportedLeague")) return "league type not supported yet";
  return "sync failed";
}
