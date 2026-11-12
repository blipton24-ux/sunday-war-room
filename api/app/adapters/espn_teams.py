"""ESPN's numeric team ids, and the team defenses built from them (ADR-053).

ESPN sends a player's NFL team as a number (`proTeamId`), and a team defense/special-teams
(D/ST) as a negative player id: `-(16000 + proTeamId)`. Our canonical spelling is nflverse's
(app/nfl_teams.py). The table below is ESPN's; it is checked against a real league in
Verification Gaps (P3 step 15).
"""

from __future__ import annotations

from app.nfl_teams import NFL_TEAMS, canonical_team

# proTeamId -> ESPN's abbreviation (as ESPN spells it; canonical_team fixes WSH, JAC, ...).
_ESPN_PRO_TEAMS: dict[int, str] = {
    1: "ATL", 2: "BUF", 3: "CHI", 4: "CIN", 5: "CLE", 6: "DAL", 7: "DEN", 8: "DET",
    9: "GB", 10: "TEN", 11: "IND", 12: "KC", 13: "LV", 14: "LAR", 15: "MIA", 16: "MIN",
    17: "NE", 18: "NO", 19: "NYG", 20: "NYJ", 21: "PHI", 22: "ARI", 23: "PIT", 24: "LAC",
    25: "SF", 26: "SEA", 27: "TB", 28: "WSH", 29: "CAR", 30: "JAX", 33: "BAL", 34: "HOU",
}  # fmt: skip

DEFENSE_ID_BASE = 16000


def team_for_pro_team_id(pro_team_id: int) -> str | None:
    """The canonical team code for ESPN's proTeamId, or None for 0 (free agent) / unknown."""
    abbr = _ESPN_PRO_TEAMS.get(pro_team_id)
    return canonical_team(abbr) if abbr else None


def defense_team(espn_player_id: str) -> str | None:
    """The team a D/ST id stands for, e.g. '-16028' -> 'WAS'. None if it isn't a D/ST id."""
    try:
        value = int(espn_player_id)
    except ValueError:
        return None
    if value >= 0:
        return None
    return team_for_pro_team_id(-value - DEFENSE_ID_BASE)


def all_pro_team_codes() -> set[str]:
    """Every canonical code the table produces (for the test that it matches nfl_teams)."""
    codes = {team_for_pro_team_id(i) for i in _ESPN_PRO_TEAMS}
    return {c for c in codes if c is not None} & set(NFL_TEAMS)
