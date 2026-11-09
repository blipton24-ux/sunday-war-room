"""One spelling per NFL team across the app: nflverse's abbreviations are canonical.

Platforms that spell a team differently are normalized at their adapter boundary.
"""

NFL_TEAMS = frozenset(
    [
        "ARI",
        "ATL",
        "BAL",
        "BUF",
        "CAR",
        "CHI",
        "CIN",
        "CLE",
        "DAL",
        "DEN",
        "DET",
        "GB",
        "HOU",
        "IND",
        "JAX",
        "KC",
        "LA",
        "LAC",
        "LV",
        "MIA",
        "MIN",
        "NE",
        "NO",
        "NYG",
        "NYJ",
        "PHI",
        "PIT",
        "SEA",
        "SF",
        "TB",
        "TEN",
        "WAS",
    ]
)

# Other spellings seen in the wild -> canonical.
_ALIASES = {"LAR": "LA", "JAC": "JAX", "WSH": "WAS", "OAK": "LV", "SD": "LAC", "STL": "LA"}


def canonical_team(code: str | None) -> str | None:
    if not code:
        return None
    code = code.strip().upper()
    return _ALIASES.get(code, code)


def defense_key(team: str) -> str:
    """Team defenses are scored like players; this is their id in player_week_stats."""
    canon = canonical_team(team)
    assert canon is not None
    return f"TEAM_{canon}"


# ESPN's CDN spells a few teams differently (headshots/logos, ADR-032).
_ESPN = {"LA": "lar", "WAS": "wsh"}


def espn_logo_url(team: str) -> str:
    return f"https://a.espncdn.com/i/teamlogos/nfl/500/{_ESPN.get(team, team.lower())}.png"


def espn_headshot_url(espn_id: str) -> str:
    return f"https://a.espncdn.com/i/headshots/nfl/players/full/{espn_id}.png"
