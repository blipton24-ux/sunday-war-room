"use client";

import { Check, LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Card, PrimaryButton, SecondaryButton } from "@/components/ui/primitives";
import { isApiError } from "@/lib/api/client";
import {
  useConnectSleeper,
  useFollowLeague,
  useJob,
  useSetMyTeam,
  useTeams,
} from "@/lib/api/queries";
import { cn } from "@/lib/cn";

interface FoundLeague {
  external_id: string;
  name: string;
  season: number;
  total_teams: number | null;
}

interface ConnectResult {
  username: string;
  sleeper_user_id: string;
  season: number;
  leagues: FoundLeague[];
}

/** Followed league: our id, its first-sync job, and the team the user picked. */
interface Followed {
  external: FoundLeague;
  leagueId: number;
  jobId: string;
}

/**
 * Onboarding (UI Screens): Sleeper username -> leagues -> pick your team in each ->
 * syncing progress -> Home. Every Sleeper call runs in the worker; this screen only
 * starts jobs and watches them.
 */
export function OnboardingFlow() {
  const router = useRouter();
  const [connectJob, setConnectJob] = useState<string | null>(null);
  const [connected, setConnected] = useState<ConnectResult | null>(null);
  const [followed, setFollowed] = useState<Followed[] | null>(null);

  if (!connected) {
    return <UsernameStep jobId={connectJob} onStarted={setConnectJob} onDone={setConnected} />;
  }
  if (!followed) {
    return <LeaguesStep found={connected} onFollowed={setFollowed} />;
  }
  return (
    <TeamsStep
      followed={followed}
      sleeperUserId={connected.sleeper_user_id}
      onDone={() => {
        router.push("/");
        router.refresh();
      }}
    />
  );
}

function StepTitle({ step, title, children }: { step: number; title: string; children?: React.ReactNode }) {
  return (
    <div>
      <p className="eyebrow">Step {step} of 3</p>
      <h1 className="page-title">{title}</h1>
      {children && <p className="mt-2 text-sm text-ink-lo">{children}</p>}
    </div>
  );
}

// --------------------------------------------------------------------------- step 1
function UsernameStep({
  jobId,
  onStarted,
  onDone,
}: {
  jobId: string | null;
  onStarted: (jobId: string) => void;
  onDone: (result: ConnectResult) => void;
}) {
  const [username, setUsername] = useState("");
  const connect = useConnectSleeper();
  const job = useJob(jobId);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (job.data?.status === "done" && job.data.result) {
      onDone(job.data.result as unknown as ConnectResult);
    } else if (job.data?.status === "failed") {
      setError(
        job.data.error?.includes("NotFoundOnPlatform")
          ? "We couldn't find a Sleeper account with that username."
          : "Sleeper didn't answer. Try again in a minute.",
      );
    }
  }, [job.data, onDone]);

  const waiting = connect.isPending || (jobId != null && !error && job.data?.status !== "done");

  return (
    <>
      <StepTitle step={1} title="Connect Sleeper">
        Your Sleeper username is all we need. Sunday War Room only reads your leagues and never
        changes anything.
      </StepTitle>
      <form
        className="flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          connect.mutate(username.trim(), {
            onSuccess: (r) => onStarted(r.job_id),
            onError: (e) => setError(isApiError(e) ? e.message : "Couldn't start. Try again."),
          });
        }}
      >
        <label htmlFor="sleeper" className="text-xs font-semibold text-sea">
          Sleeper username
        </label>
        <input
          id="sleeper"
          required
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="your_sleeper_name"
          className="min-h-12 rounded-[14px] bg-raised px-4 text-base outline-none ring-accent/50 placeholder:text-ink-faint focus:ring-2"
        />
        <PrimaryButton type="submit" disabled={waiting || !username.trim()}>
          {waiting ? (
            <>
              <LoaderCircle className="size-4 animate-spin" /> Looking up your leagues…
            </>
          ) : (
            "Find my leagues"
          )}
        </PrimaryButton>
        {error && <p className="text-sm text-bad">{error}</p>}
      </form>
    </>
  );
}

// --------------------------------------------------------------------------- step 2
function LeaguesStep({
  found,
  onFollowed,
}: {
  found: ConnectResult;
  onFollowed: (followed: Followed[]) => void;
}) {
  const [picked, setPicked] = useState<Set<string>>(() => new Set(found.leagues.map((l) => l.external_id)));
  const follow = useFollowLeague();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const results: Followed[] = [];
      for (const league of found.leagues.filter((l) => picked.has(l.external_id))) {
        const r = await follow.mutateAsync(league.external_id);
        results.push({ external: league, leagueId: r.league.id, jobId: r.job_id });
      }
      onFollowed(results);
    } catch (e) {
      setError(isApiError(e) ? e.message : "Couldn't follow those leagues. Try again.");
      setBusy(false);
    }
  }

  if (found.leagues.length === 0) {
    return (
      <>
        <StepTitle step={2} title="No leagues yet">
          {found.username} has no Sleeper leagues for the {found.season} season.
        </StepTitle>
        <SecondaryButton onClick={() => window.location.reload()}>Try another username</SecondaryButton>
      </>
    );
  }

  return (
    <>
      <StepTitle step={2} title="Pick your leagues">
        Found {found.leagues.length} league{found.leagues.length > 1 ? "s" : ""} for{" "}
        <b className="text-ink">{found.username}</b> in {found.season}.
      </StepTitle>
      <div className="flex flex-col gap-2">
        {found.leagues.map((l) => {
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
                  {l.season}
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

// --------------------------------------------------------------------------- step 3
function TeamsStep({
  followed,
  sleeperUserId,
  onDone,
}: {
  followed: Followed[];
  sleeperUserId: string;
  onDone: () => void;
}) {
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
            sleeperUserId={sleeperUserId}
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

function LeagueTeamPicker({
  followed,
  sleeperUserId,
  onChosen,
}: {
  followed: Followed;
  sleeperUserId: string;
  onChosen: () => void;
}) {
  const job = useJob(followed.jobId);
  const synced = job.data?.status === "done";
  const teams = useTeams(synced ? followed.leagueId : null);
  const setTeam = useSetMyTeam();
  const [teamId, setTeamId] = useState<number | null>(null);
  const [saved, setSaved] = useState(false);

  // Pre-select the team the connected Sleeper user owns.
  useEffect(() => {
    if (teamId == null && teams.data) {
      const mine = teams.data.find((t) => t.owner_external_id === sleeperUserId);
      if (mine) setTeamId(mine.id);
    }
  }, [teams.data, sleeperUserId, teamId]);

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
          <span className="text-xs text-bad">sync failed</span>
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
                  {t.owner_external_id === sleeperUserId ? " · you" : ""}
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
