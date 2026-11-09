"use client";

import { Check, Download, Share } from "lucide-react";

import { useInstall } from "@/components/install-provider";
import { Card, SecondaryButton } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";

/** Settings: install Sunday War Room to the home screen (the PWA, ADR-010). */
export function InstallCard() {
  const { state, install } = useInstall();
  const toast = useToast();

  if (state === "installed") {
    return (
      <Card className="flex items-center gap-3">
        <span className="grid size-9 shrink-0 place-items-center rounded-full bg-good/15 text-good">
          <Check className="size-5" aria-hidden />
        </span>
        <div>
          <div className="font-semibold">Installed</div>
          <div className="text-sm text-ink-lo">You&apos;re using Sunday War Room as an app.</div>
        </div>
      </Card>
    );
  }
  return (
    <Card>
      <div className="font-semibold">Add it to your home screen</div>
      <p className="mt-1 text-sm text-ink-lo">
        Opens full screen like an app, with its own icon. Same data, nothing extra to download.
      </p>
      {state === "can-prompt" && (
        <SecondaryButton
          className="mt-3 w-full"
          onClick={async () => {
            const outcome = await install();
            if (outcome === "accepted") toast("Installed. Look for it on your home screen.");
          }}
        >
          <Download className="size-4" aria-hidden /> Install app
        </SecondaryButton>
      )}
      {state === "ios" && (
        <p className="mt-3 flex items-start gap-2 rounded-xl bg-overlay px-3 py-2.5 text-sm text-ink-mid">
          <Share className="mt-0.5 size-4 shrink-0 text-accent" aria-hidden />
          <span>
            In Safari, tap the <b className="text-ink">Share</b> button, then{" "}
            <b className="text-ink">Add to Home Screen</b>.
          </span>
        </p>
      )}
      {state === "manual" && (
        <p className="mt-3 rounded-xl bg-overlay px-3 py-2.5 text-sm text-ink-mid">
          Open your browser&apos;s menu and choose <b className="text-ink">Install app</b> or{" "}
          <b className="text-ink">Add to Home Screen</b>.
        </p>
      )}
    </Card>
  );
}
