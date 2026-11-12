import Link from "next/link";

import { Logo, Wordmark } from "@/components/shell/logo";
import { requireSession } from "@/lib/server/session";

import { OnboardingFlow } from "./onboarding-flow";
import type { Stage } from "./types";

export const metadata = { title: "Connect your league" };
export const dynamic = "force-dynamic";

/** `?platform=espn&cookies=1` (the emailed link) opens the cookie step directly. */
function initialStage(params: { platform?: string; cookies?: string }): Stage {
  if (params.platform === "espn") return params.cookies ? "espn-cookies" : "espn-link";
  if (params.platform === "sleeper") return "sleeper";
  return "platform";
}

export default async function OnboardingPage({
  searchParams,
}: {
  searchParams: Promise<{ platform?: string; cookies?: string }>;
}) {
  await requireSession();
  const stage = initialStage(await searchParams);
  return (
    <div className="min-h-dvh">
      <header className="border-b border-accent/20">
        <div className="mx-auto flex max-w-xl items-center gap-3 px-4 py-2.5">
          <Link href="/" aria-label="Home">
            <Logo size={36} className="rounded-xl" />
          </Link>
          <Wordmark />
        </div>
      </header>
      <main className="mx-auto flex max-w-xl flex-col gap-4 px-4 pb-16 pt-6">
        <OnboardingFlow initialStage={stage} />
      </main>
    </div>
  );
}
