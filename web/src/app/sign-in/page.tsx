import { redirect } from "next/navigation";

import { Logo, Wordmark } from "@/components/shell/logo";
import { env, googleEnabled } from "@/lib/server/env";
import { getSession } from "@/lib/server/session";

import { SignInForm } from "./sign-in-form";

export const metadata = { title: "Sign in" };
export const dynamic = "force-dynamic";

export default async function SignInPage() {
  if (await getSession()) redirect("/");
  return (
    <main className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center gap-8 px-5 py-10">
      <div className="flex flex-col items-center gap-3 text-center">
        <Logo size={72} className="rounded-2xl" />
        <Wordmark />
        <p className="text-sm text-ink-lo">
          Start/sit calls, matchup odds and projections that explain themselves, for your Sleeper
          leagues.
        </p>
      </div>
      <SignInForm
        googleEnabled={googleEnabled()}
        devLinkHint={!env.isProduction && !env.resendApiKey}
      />
      <p className="text-center text-[0.72rem] text-ink-faint">
        Read-only: Sunday War Room never changes anything in your league.
      </p>
    </main>
  );
}
