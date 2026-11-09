"use client";

import { ErrorState } from "@/components/ui/primitives";

/** Shown when a signed-in page fails to load on the server (e.g. the API is unreachable). */
export default function SignedInError({ reset }: { error: Error; reset: () => void }) {
  return (
    <ErrorState
      title="We couldn't load your war room"
      message="The data service didn't answer. Your leagues are safe; try again in a moment."
      onRetry={reset}
    />
  );
}
