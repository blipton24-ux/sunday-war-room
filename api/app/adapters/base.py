"""The platform-agnostic league interface (ADR-006, docs/Concepts/Adapter-Pattern.md).

Everything outside `app/adapters/` sees only these types, never a platform's raw JSON.
"""

from dataclasses import dataclass, field
from typing import Literal, Protocol

Platform = Literal["sleeper", "espn", "yahoo"]

# Lineup slots Sunday War Room understands. Platforms map their names onto these.
STARTER_SLOTS = {"QB", "RB", "WR", "TE", "K", "DEF", "FLEX", "SUPER_FLEX", "REC_FLEX", "WRRB_FLEX"}
BENCH, IR, TAXI = "BN", "IR", "TAXI"


class AdapterError(Exception):
    """The platform couldn't be reached or refused the request (retryable)."""


class AdapterSchemaError(AdapterError):
    """The platform's response no longer has the shape we expect: fail loudly, don't guess."""


class NotFoundOnPlatform(AdapterError):
    """The username / league id doesn't exist on the platform."""


@dataclass(frozen=True)
class PlatformUser:
    external_user_id: str
    username: str
    display_name: str


@dataclass(frozen=True)
class LeagueRef:
    platform: Platform
    external_id: str
    season: int
    name: str
    total_teams: int | None = None


@dataclass(frozen=True)
class LeagueData:
    ref: LeagueRef
    avatar_url: str | None
    # Platform rule name -> points. Interpreted by app/model/scoring.py for this platform.
    scoring_rules: dict[str, float]
    # One entry per lineup position in order, e.g. ["QB","RB","RB",...,"BN","BN"].
    roster_slots: list[str]
    status: str  # pre_draft / drafting / in_season / complete


@dataclass(frozen=True)
class RosterSpot:
    player_external_id: str
    slot: str  # one of STARTER_SLOTS, or BN / IR / TAXI
    is_starter: bool


@dataclass(frozen=True)
class TeamData:
    external_id: str
    owner_external_id: str | None
    name: str
    owner_name: str | None
    avatar_url: str | None
    wins: int
    losses: int
    ties: int
    roster: list[RosterSpot] = field(default_factory=list)


@dataclass(frozen=True)
class MatchupData:
    week: int
    matchup_key: str | None  # teams sharing a key play each other; None = bye/no opponent
    team_external_id: str
    points: float | None
    # Starters actually set for that week (historical weeks), in slot order.
    roster: list[RosterSpot] = field(default_factory=list)


@dataclass(frozen=True)
class PlayerData:
    external_id: str
    name: str
    position: str | None
    nfl_team: str | None
    status: str | None
    injury_status: str | None
    gsis_id: str | None
    espn_id: str | None
    yahoo_id: str | None
    depth_chart_order: int | None


@dataclass(frozen=True)
class NflState:
    season: int
    week: int
    season_type: str  # pre / regular / post / off


class LeagueAdapter(Protocol):
    platform: Platform

    async def find_user(self, username: str) -> PlatformUser: ...
    async def find_leagues(self, user: PlatformUser, season: int) -> list[LeagueRef]: ...
    async def fetch_league(self, external_id: str) -> LeagueData: ...
    async def fetch_teams(self, league: LeagueData) -> list[TeamData]: ...
    async def fetch_matchups(self, league: LeagueData, week: int) -> list[MatchupData]: ...
    async def fetch_players(self) -> list[PlayerData]: ...
    async def fetch_state(self) -> NflState: ...
