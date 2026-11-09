import Link from "next/link";

import { Logo, Wordmark } from "@/components/shell/logo";
import { requireSession } from "@/lib/server/session";

import { OnboardingFlow } from "./onboarding-flow";

export const metadata = { title: "Connect your league" };
export const dynamic = "force-dynamic";

export default async function OnboardingPage() {
  await requireSession();
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
        <OnboardingFlow />
      </main>
    </div>
  );
}
