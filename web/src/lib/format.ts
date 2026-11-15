/** Small display helpers shared by every screen. Pure functions (unit tested). */

const PLATFORM_NAMES: Record<string, string> = { sleeper: "Sleeper", espn: "ESPN", yahoo: "Yahoo" };

/** A platform's display name ("espn" -> "ESPN"). Unknown platforms are shown as given. */
export function platformName(platform: string): string {
  return PLATFORM_NAMES[platform] ?? platform;
}

export function f1(n: number | null | undefined): string {
  return n == null || Number.isNaN(n) ? "--" : n.toFixed(1);
}

export function pct(p: number | null | undefined): string {
  return p == null ? "--" : `${Math.round(p * 100)}%`;
}

export function signed(n: number): string {
  return `${n >= 0 ? "+" : "−"}${Math.abs(n).toFixed(1)}`;
}

/** "just now", "3m ago", "2h ago", "4d ago" (null: "never"). */
export function timeAgo(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return "never";
  const seconds = Math.max(0, (now.getTime() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

/** "Amon-Ra St. Brown" -> "AS"; "Steelers" -> "ST"; at most two letters. */
export function initials(name: string): string {
  const words = name.split(/\s+/).filter((w) => /^[A-Za-z]/.test(w));
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0]!.slice(0, 2).toUpperCase();
  return (words[0]![0]! + words[words.length - 1]![0]!).toUpperCase();
}

/** First name dropped for tight spaces: "Jauan Jennings" -> "Jennings". */
export function lastName(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length < 2) return name;
  const suffix = /^(jr\.?|sr\.?|ii|iii|iv|v)$/i;
  const last = parts[parts.length - 1]!;
  return suffix.test(last) && parts.length > 2 ? parts[parts.length - 2]! : last;
}

export function kickoffLabel(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}
