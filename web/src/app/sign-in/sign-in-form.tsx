"use client";

import { MailCheck } from "lucide-react";
import { useState } from "react";

import { Card, PrimaryButton, SecondaryButton } from "@/components/ui/primitives";
import { authClient } from "@/lib/auth-client";

export function SignInForm({
  googleEnabled,
  devLinkHint,
}: {
  googleEnabled: boolean;
  devLinkHint: boolean;
}) {
  const [email, setEmail] = useState("");
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function sendLink(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const { error } = await authClient.signIn.magicLink({ email, callbackURL: "/" });
    setBusy(false);
    if (error) setError(error.message ?? "Couldn't send the link. Try again.");
    else setSentTo(email);
  }

  if (sentTo) {
    return (
      <Card className="text-center">
        <div className="accent-soft mx-auto mb-3 grid size-12 place-items-center rounded-full text-accent">
          <MailCheck className="size-6" aria-hidden />
        </div>
        <p className="font-bold">Check your inbox</p>
        <p className="mt-1 text-sm text-ink-lo">
          We sent a sign-in link to <b className="text-ink">{sentTo}</b>. It works once and expires
          in 10 minutes.
        </p>
        {devLinkHint && (
          <p className="mt-3 rounded-xl bg-high px-3 py-2 text-xs text-ink-mid">
            Local development: no email service is configured, so the link is printed in the web
            server&apos;s terminal.
          </p>
        )}
        <button onClick={() => setSentTo(null)} className="mt-4 text-sm font-semibold text-accent">
          Use a different email
        </button>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {googleEnabled && (
        <>
          <SecondaryButton
            className="w-full bg-raised text-[0.95rem] text-ink"
            onClick={() => authClient.signIn.social({ provider: "google", callbackURL: "/" })}
          >
            <GoogleMark /> Sign in with Google
          </SecondaryButton>
          <div className="flex items-center gap-3 text-xs text-ink-faint">
            <span className="h-px flex-1 bg-line-strong" /> or <span className="h-px flex-1 bg-line-strong" />
          </div>
        </>
      )}
      <form onSubmit={sendLink} className="flex flex-col gap-3">
        <label className="text-xs font-semibold text-sea" htmlFor="email">
          Email
        </label>
        <input
          id="email"
          type="email"
          required
          autoComplete="email"
          inputMode="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="min-h-12 rounded-[14px] bg-raised px-4 text-base outline-none ring-accent/50 placeholder:text-ink-faint focus:ring-2"
        />
        <PrimaryButton type="submit" disabled={busy}>
          {busy ? "Sending…" : "Email me a link"}
        </PrimaryButton>
        {error && <p className="text-sm text-bad">{error}</p>}
      </form>
    </div>
  );
}

function GoogleMark() {
  return (
    <svg viewBox="0 0 24 24" className="size-5" aria-hidden>
      <path fill="#EA4335" d="M12 10.2v3.9h5.5c-.2 1.3-1.6 3.9-5.5 3.9-3.3 0-6-2.7-6-6.1s2.7-6.1 6-6.1c1.9 0 3.1.8 3.8 1.5l2.6-2.5C16.8 3.3 14.6 2.3 12 2.3 6.7 2.3 2.4 6.6 2.4 12s4.3 9.7 9.6 9.7c5.5 0 9.2-3.9 9.2-9.4 0-.6-.1-1.1-.2-1.6H12z" />
    </svg>
  );
}
