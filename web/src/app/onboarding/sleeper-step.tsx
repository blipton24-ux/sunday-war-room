"use client";

import { LoaderCircle } from "lucide-react";
import { useEffect, useState } from "react";

import { PrimaryButton } from "@/components/ui/primitives";
import { isApiError } from "@/lib/api/client";
import { useConnectSleeper, useJob } from "@/lib/api/queries";
import { readLeagues } from "@/lib/espn";

import { StepTitle } from "./steps";
import type { Offer } from "./types";

/** Sleeper: a username is all it takes (its API is public). */
export function SleeperStep({ onDone }: { onDone: (offer: Offer) => void }) {
  const [username, setUsername] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const connect = useConnectSleeper();
  const job = useJob(jobId);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (job.data?.status === "done" && job.data.result) {
      const result = job.data.result as { username?: string; sleeper_user_id?: string; season?: number };
      onDone({
        platform: "sleeper",
        label: result.username ?? null,
        season: result.season ?? 0,
        leagues: readLeagues(job.data.result) ?? [],
        ownerId: result.sleeper_user_id ?? null,
      });
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
            onSuccess: (r) => setJobId(r.job_id),
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
