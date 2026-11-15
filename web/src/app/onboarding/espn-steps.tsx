"use client";

import { Copy, LoaderCircle, Mail, MonitorSmartphone } from "lucide-react";
import Image from "next/image";
import { useEffect, useState } from "react";

import { Card, PrimaryButton, SecondaryButton } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";
import { isApiError } from "@/lib/api/client";
import { useConnectEspn, useEmailEspnLink, useJob, useProbeEspn } from "@/lib/api/queries";
import {
  BROWSER_NAMES,
  COOKIE_CONSENT,
  cookieSteps,
  detectBrowser,
  espnConnectPath,
  isPhoneLike,
  readLeagues,
  readProbe,
  type BrowserKind,
  type FoundLeague,
} from "@/lib/espn";

import { StepTitle } from "./steps";
import type { Offer } from "./types";

const inputClass =
  "min-h-12 rounded-[14px] bg-raised px-4 text-base outline-none ring-accent/50 placeholder:text-ink-faint focus:ring-2";

// --------------------------------------------------------------------------- 1a: league link
/**
 * ESPN, link first (ADR-051): paste a league link. A public league connects right away with no
 * login; a private one sends the user to the cookie step.
 */
export function EspnLinkStep({
  onPublic,
  onPrivate,
}: {
  onPublic: (offer: Offer) => void;
  onPrivate: () => void;
}) {
  const [link, setLink] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [unsupported, setUnsupported] = useState<string | null>(null);
  const probe = useProbeEspn();
  const job = useJob(jobId);

  useEffect(() => {
    if (job.data?.status === "done") {
      const outcome = readProbe(job.data.result);
      if (outcome?.kind === "public") {
        onPublic({ platform: "espn", label: null, season: outcome.league.season, leagues: [outcome.league] });
      } else if (outcome?.kind === "private") {
        onPrivate();
      } else if (outcome?.kind === "unsupported") {
        setUnsupported(outcome.message);
      } else {
        setError("ESPN's answer wasn't what we expected. Try again in a minute.");
      }
    } else if (job.data?.status === "failed") {
      setError(
        job.data.error?.includes("NotFoundOnPlatform")
          ? "ESPN doesn't know that league for this season. Check the link and try again."
          : "ESPN didn't answer. Try again in a minute.",
      );
    }
  }, [job.data, onPublic, onPrivate]);

  const waiting = probe.isPending || (jobId != null && !error && !unsupported && job.data?.status !== "done");

  return (
    <>
      <StepTitle step={1} title="Connect ESPN">
        Paste a link to your league. Open your league on ESPN and copy the address from your browser.
      </StepTitle>
      <form
        className="flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          setUnsupported(null);
          setJobId(null);
          probe.mutate(link.trim(), {
            onSuccess: (r) => setJobId(r.job_id),
            onError: (e) => setError(isApiError(e) ? e.message : "Couldn't start. Try again."),
          });
        }}
      >
        <label htmlFor="espn-link" className="text-xs font-semibold text-sea">
          ESPN league link
        </label>
        <input
          id="espn-link"
          required
          inputMode="url"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          value={link}
          onChange={(e) => setLink(e.target.value)}
          placeholder="https://fantasy.espn.com/football/league?leagueId=…"
          className={inputClass}
        />
        <PrimaryButton type="submit" disabled={waiting || !link.trim()}>
          {waiting ? (
            <>
              <LoaderCircle className="size-4 animate-spin" /> Checking your league…
            </>
          ) : (
            "Check my league"
          )}
        </PrimaryButton>
        {error && <p className="text-sm text-bad">{error}</p>}
        {unsupported && <p className="text-sm text-warn">{unsupported}</p>}
      </form>
      <button
        type="button"
        onClick={onPrivate}
        className="self-start text-sm font-semibold text-accent"
      >
        My league is private, or I want to find all my leagues
      </button>
    </>
  );
}

// --------------------------------------------------------------------------- 1b: cookies
/** Private leagues: a guided copy-and-paste of the two ESPN cookies (ADR-051). */
export function EspnCookiesStep({
  fromPrivateLink,
  onDone,
}: {
  fromPrivateLink?: boolean;
  onDone: (offer: Offer) => void;
}) {
  const [browser, setBrowser] = useState<BrowserKind>("chrome");
  const [phone, setPhone] = useState(false);
  const [forceDesktop, setForceDesktop] = useState(false);

  useEffect(() => {
    setBrowser(detectBrowser(navigator.userAgent));
    setPhone(isPhoneLike(window.matchMedia("(pointer: coarse)").matches, window.innerWidth));
  }, []);

  if (phone && !forceDesktop) {
    return <NeedsComputer onContinue={() => setForceDesktop(true)} />;
  }
  return (
    <CookieForm browser={browser} fromPrivateLink={fromPrivateLink} onDone={onDone} />
  );
}

function CookieForm({
  browser,
  fromPrivateLink,
  onDone,
}: {
  browser: BrowserKind;
  fromPrivateLink?: boolean;
  onDone: (offer: Offer) => void;
}) {
  const [s2, setS2] = useState("");
  const [swid, setSwid] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const connect = useConnectEspn();
  const job = useJob(jobId);

  useEffect(() => {
    if (job.data?.status === "done") {
      const leagues: FoundLeague[] | null = readLeagues(job.data.result);
      const season = (job.data.result as { season?: number } | null)?.season ?? 0;
      if (leagues) onDone({ platform: "espn", label: null, season, leagues });
      else setError("ESPN's answer wasn't what we expected. Try again in a minute.");
    } else if (job.data?.status === "failed") {
      setError(
        job.data.error?.includes("CredentialsInvalid")
          ? "ESPN didn't accept those values. Make sure you're signed in to ESPN, then copy both values again."
          : "ESPN didn't answer. Try again in a minute.",
      );
    }
  }, [job.data, onDone]);

  const waiting = connect.isPending || (jobId != null && !error && job.data?.status !== "done");

  return (
    <>
      <StepTitle step={1} title="Connect your private ESPN league">
        {fromPrivateLink
          ? "That league is private, so ESPN only shows it to you when you're signed in. "
          : ""}
        ESPN doesn&apos;t offer a &ldquo;sign in with ESPN&rdquo; button, so we need two values
        from your browser. It takes about two minutes, and you only do it once in a while.
      </StepTitle>

      <Card className="flex flex-col gap-3">
        <h2 className="font-semibold">How to copy them in {BROWSER_NAMES[browser]}</h2>
        <ol className="list-decimal space-y-2 pl-5 text-sm text-ink-mid">
          {cookieSteps(browser).map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
        <Image
          src="/help/espn/cookies.svg"
          alt="A diagram of the developer tools: the Application tab, Cookies on the left, and the espn_s2 and SWID rows highlighted"
          width={640}
          height={300}
          unoptimized
          className="w-full rounded-xl"
        />
      </Card>

      <form
        className="flex flex-col gap-3"
        autoComplete="off"
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          setJobId(null);
          connect.mutate(
            { espn_s2: s2.trim(), swid: swid.trim() },
            {
              onSuccess: (r) => setJobId(r.job_id),
              onError: (e) =>
                setError(isApiError(e) ? e.message : "Couldn't save those. Try again."),
            },
          );
        }}
      >
        <label htmlFor="espn-s2" className="text-xs font-semibold text-sea">
          espn_s2 (the long one)
        </label>
        <input
          id="espn-s2"
          required
          type="password"
          autoComplete="off"
          data-1p-ignore
          spellCheck={false}
          value={s2}
          onChange={(e) => setS2(e.target.value)}
          className={inputClass}
        />
        <label htmlFor="espn-swid" className="text-xs font-semibold text-sea">
          SWID (looks like {"{XXXXXXXX-XXXX-…}"})
        </label>
        <input
          id="espn-swid"
          required
          type="password"
          autoComplete="off"
          data-1p-ignore
          spellCheck={false}
          value={swid}
          onChange={(e) => setSwid(e.target.value)}
          className={inputClass}
        />
        <p className="text-xs text-ink-lo">{COOKIE_CONSENT}</p>
        <PrimaryButton type="submit" disabled={waiting || !s2.trim() || !swid.trim()}>
          {waiting ? (
            <>
              <LoaderCircle className="size-4 animate-spin" /> Checking with ESPN…
            </>
          ) : (
            "Connect ESPN"
          )}
        </PrimaryButton>
        {error && (
          <p role="alert" className="text-sm text-bad">
            {error}
          </p>
        )}
      </form>
    </>
  );
}

// --------------------------------------------------------------------------- phone
/** Copying cookies can't be done on a phone: offer to email the link, or copy it (ADR-051). */
function NeedsComputer({ onContinue }: { onContinue: () => void }) {
  const email = useEmailEspnLink();
  const toast = useToast();

  async function copyLink() {
    const url = new URL(espnConnectPath(), window.location.origin).toString();
    try {
      await navigator.clipboard.writeText(url);
      toast("Link copied");
    } catch {
      toast("Couldn't copy. Use the email button instead.");
    }
  }

  return (
    <>
      <StepTitle step={1} title="Finish this on a computer">
        Connecting a private ESPN league means copying two values from your browser&apos;s developer
        tools, and a phone can&apos;t do that. Open Sunday War Room on a computer where you&apos;re
        signed in to ESPN to finish.
      </StepTitle>
      <Card className="flex flex-col gap-3">
        <PrimaryButton
          disabled={email.isPending}
          onClick={() =>
            email.mutate(undefined, {
              onSuccess: () => toast("Sent. Open it on your computer."),
              onError: (e) => toast(e instanceof Error ? e.message : "Couldn't send the email."),
            })
          }
        >
          <Mail className="size-4" /> {email.isPending ? "Sending…" : "Email me a link"}
        </PrimaryButton>
        <SecondaryButton onClick={copyLink}>
          <Copy className="size-4" /> Copy the link
        </SecondaryButton>
        <button
          type="button"
          onClick={onContinue}
          className="flex items-center justify-center gap-2 text-sm font-semibold text-accent"
        >
          <MonitorSmartphone className="size-4" /> I&apos;m on a computer anyway
        </button>
      </Card>
    </>
  );
}
