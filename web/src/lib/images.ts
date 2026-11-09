/**
 * ESPN team-logo URLs for the small logo beside a player's name (ADR-032/037). Same rule as
 * the API's app/nfl_teams.py: ESPN's CDN spells the Rams and Washington differently.
 */
const ESPN_CODE: Record<string, string> = { LA: "lar", WAS: "wsh" };

export function espnLogo(team: string): string {
  return `https://a.espncdn.com/i/teamlogos/nfl/500/${ESPN_CODE[team] ?? team.toLowerCase()}.png`;
}
