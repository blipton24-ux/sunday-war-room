/**
 * Team colors for the flat tint behind player photos (ADR-032). Keys are the API's
 * canonical team codes (nflverse spelling: LA for the Rams, WAS for Washington).
 * Mid-tone variants are used where a team's darkest color would vanish as a 25% tint.
 */
export const TEAM_COLORS: Record<string, string> = {
  ARI: "#C0284B", ATL: "#E0263A", BAL: "#6A4BC4", BUF: "#1E5BD8",
  CAR: "#0085CA", CHI: "#E64100", CIN: "#FB4F14", CLE: "#FF3C00",
  DAL: "#2F72D6", DEN: "#FB4F14", DET: "#0076B6", GB: "#3B7A57",
  HOU: "#A71930", IND: "#2E6FD1", JAX: "#00839C", KC: "#E31837",
  LA: "#2F6BDB", LAC: "#0080C6", LV: "#A5ACAF", MIA: "#008E97",
  MIN: "#7A4FC4", NE: "#C60C30", NO: "#D3BC8D", NYG: "#2856B5",
  NYJ: "#1E7A4F", PHI: "#00838F", PIT: "#FFB612", SEA: "#69BE28",
  SF: "#C8102E", TB: "#D50A0A", TEN: "#4B92DB", WAS: "#8C2B3C",
}; // prettier-ignore

const NEUTRAL = "#64748b";

export function teamColor(team: string | null | undefined): string {
  return (team && TEAM_COLORS[team]) || NEUTRAL;
}

/** Hex color + alpha byte, e.g. tint("#2F6BDB", 0.25) -> "#2F6BDB40". */
export function tint(color: string, alpha: number): string {
  const byte = Math.round(Math.max(0, Math.min(1, alpha)) * 255);
  return `${color}${byte.toString(16).padStart(2, "0")}`;
}
