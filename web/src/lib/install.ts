/**
 * What the "Install the app" card should offer on this device. Pure (unit tested); the
 * browser facts come from components/install-provider.tsx.
 */
export type InstallState =
  | "installed" // already running as an installed app
  | "can-prompt" // the browser gave us an install prompt: show an Install button
  | "ios" // iPhone/iPad Safari: no prompt exists, show the Share-sheet steps
  | "manual"; // anything else: point at the browser menu

export interface InstallFacts {
  standalone: boolean;
  hasPrompt: boolean;
  ios: boolean;
}

export function installState({ standalone, hasPrompt, ios }: InstallFacts): InstallState {
  if (standalone) return "installed";
  if (hasPrompt) return "can-prompt";
  if (ios) return "ios";
  return "manual";
}

/** iPhone, iPad and iPadOS (which reports itself as a Mac with a touch screen). */
export function isIos(userAgent: string, platform: string, maxTouchPoints: number): boolean {
  return /iphone|ipad|ipod/i.test(userAgent) || (platform === "MacIntel" && maxTouchPoints > 1);
}
