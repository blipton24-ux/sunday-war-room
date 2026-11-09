/**
 * Lineup slots and position colors (identical everywhere, UI Screens spec). Class names are
 * written out in full so Tailwind can see them.
 */

const BG: Record<string, string> = {
  QB: "bg-pos-qb", RB: "bg-pos-rb", WR: "bg-pos-wr", TE: "bg-pos-te",
  K: "bg-pos-k", DEF: "bg-pos-def", FLEX: "bg-pos-flex", SUPER_FLEX: "bg-pos-flex",
  REC_FLEX: "bg-pos-flex", WRRB_FLEX: "bg-pos-flex",
}; // prettier-ignore

// Text versions of the position colors: theme-aware so they stay readable on both backgrounds.
const TEXT: Record<string, string> = {
  QB: "text-pos-qb-fg", RB: "text-pos-rb-fg", WR: "text-pos-wr-fg", TE: "text-pos-te-fg",
  K: "text-pos-k-fg", DEF: "text-pos-def-fg",
}; // prettier-ignore

const SHORT: Record<string, string> = {
  SUPER_FLEX: "SF", REC_FLEX: "R/T", WRRB_FLEX: "W/R", TAXI: "TX", DEF: "DST",
};

/** Background class for a slot or position tag (bench, IR and taxi share a neutral). */
export function slotBg(slot: string): string {
  return BG[slot] ?? "bg-pos-bn";
}

export function positionText(position: string | null | undefined): string {
  return (position && TEXT[position]) || "text-ink-lo";
}

export function slotLabel(slot: string): string {
  return SHORT[slot] ?? slot;
}

export function positionLabel(position: string | null | undefined): string {
  if (!position) return "";
  return position === "DEF" ? "DST" : position;
}

export const BENCH_SLOTS = new Set(["BN", "IR", "TAXI"]);
