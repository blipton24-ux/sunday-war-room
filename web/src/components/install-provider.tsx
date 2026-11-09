"use client";

/**
 * Service worker registration and the browser's install prompt.
 *
 * `beforeinstallprompt` can fire before the Settings screen exists, so it is captured here,
 * at the root, and handed to whichever screen wants it.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { installState, isIos, type InstallState } from "@/lib/install";

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

interface InstallContext {
  state: InstallState;
  /** Opens the browser's install dialog. Resolves to what the user chose. */
  install: () => Promise<"accepted" | "dismissed" | "unavailable">;
}

const Ctx = createContext<InstallContext>({ state: "manual", install: async () => "unavailable" });

export function InstallProvider({ children }: { children: React.ReactNode }) {
  const [prompt, setPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [standalone, setStandalone] = useState(false);
  const [ios, setIos] = useState(false);

  useEffect(() => {
    // Production only: a service worker in development would serve stale files while editing.
    if (process.env.NODE_ENV === "production" && "serviceWorker" in navigator) {
      void navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" });
    }

    const media = window.matchMedia("(display-mode: standalone)");
    const readStandalone = () =>
      setStandalone(media.matches || (navigator as { standalone?: boolean }).standalone === true);
    readStandalone();
    media.addEventListener("change", readStandalone);
    setIos(isIos(navigator.userAgent, navigator.platform, navigator.maxTouchPoints));

    const onPrompt = (e: Event) => {
      e.preventDefault(); // keep the event so Settings can show it on demand
      setPrompt(e as BeforeInstallPromptEvent);
    };
    const onInstalled = () => {
      setPrompt(null);
      setStandalone(true);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      media.removeEventListener("change", readStandalone);
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  const install = useCallback(async () => {
    if (!prompt) return "unavailable" as const;
    await prompt.prompt();
    const { outcome } = await prompt.userChoice;
    setPrompt(null); // a prompt event can be used only once
    return outcome;
  }, [prompt]);

  const value = useMemo<InstallContext>(
    () => ({ state: installState({ standalone, hasPrompt: prompt != null, ios }), install }),
    [standalone, prompt, ios, install],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useInstall(): InstallContext {
  return useContext(Ctx);
}
