"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Card } from "@/components/ui/primitives";

import { EspnCookiesStep, EspnLinkStep } from "./espn-steps";
import { SleeperStep } from "./sleeper-step";
import { LeaguesStep, TeamsStep } from "./steps";
import type { Followed, Offer, Platform, Stage } from "./types";

/**
 * Onboarding (UI Screens): pick a platform, connect it, pick your leagues, pick your team in
 * each, then Home. Every platform call runs in the worker; these screens only start jobs and
 * watch them.
 *
 *   Sleeper  username -> leagues -> team
 *   ESPN     league link -> (public: leagues | private: copy two cookies) -> leagues -> team
 */
export function OnboardingFlow({ initialStage = "platform" }: { initialStage?: Stage }) {
  const router = useRouter();
  const [stage, setStage] = useState<Stage>(initialStage);
  const [fromPrivateLink, setFromPrivateLink] = useState(false);
  const [offer, setOffer] = useState<Offer | null>(null);
  const [followed, setFollowed] = useState<Followed[] | null>(null);

  if (followed) {
    return (
      <TeamsStep
        followed={followed}
        onDone={() => {
          router.push("/");
          router.refresh();
        }}
      />
    );
  }
  if (offer) return <LeaguesStep offer={offer} onFollowed={setFollowed} />;

  switch (stage) {
    case "sleeper":
      return <SleeperStep onDone={setOffer} />;
    case "espn-link":
      return (
        <EspnLinkStep
          onPublic={setOffer}
          onPrivate={() => {
            setFromPrivateLink(true);
            setStage("espn-cookies");
          }}
        />
      );
    case "espn-cookies":
      return <EspnCookiesStep fromPrivateLink={fromPrivateLink} onDone={setOffer} />;
    default:
      return <PlatformStep onPick={(p) => setStage(p === "sleeper" ? "sleeper" : "espn-link")} />;
  }
}

function PlatformStep({ onPick }: { onPick: (platform: Platform) => void }) {
  return (
    <>
      <div>
        <p className="eyebrow">Connect a league</p>
        <h1 className="page-title">Where do you play?</h1>
        <p className="mt-2 text-sm text-ink-lo">
          Sunday War Room only reads your leagues. It never changes your lineup or touches your
          roster.
        </p>
      </div>
      <div className="flex flex-col gap-2">
        <PlatformCard
          name="Sleeper"
          note="Just your username."
          onClick={() => onPick("sleeper")}
        />
        <PlatformCard
          name="ESPN"
          note="A link to your league. Private leagues need one extra step."
          onClick={() => onPick("espn")}
        />
        <Card className="text-sm text-ink-lo">Yahoo is coming later.</Card>
      </div>
    </>
  );
}

function PlatformCard({
  name,
  note,
  onClick,
}: {
  name: string;
  note: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex min-h-16 flex-col items-start gap-0.5 rounded-[1.25rem] bg-raised p-4 text-left shadow-card hover:accent-ring"
    >
      <span className="font-display text-lg font-extrabold [font-stretch:112%]">{name}</span>
      <span className="text-sm text-ink-lo">{note}</span>
    </button>
  );
}
