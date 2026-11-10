"""The platform-agnostic league interface (ADR-006, docs/Concepts/Adapter-Pattern.md).

Everything outside `app/adapters/` sees only these types, never a platform's raw JSON.
"""

from dataclasses import dataclass, field
from datetime import datetime
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


WaiverKind = Literal["rolling", "reverse_standings", "faab", "none"]
LeagueKind = Literal["redraft", "keeper", "dynasty"]
PlayoffRound = Literal["one_week", "two_week_final", "two_week_rounds"]


@dataclass(frozen=True)
class WaiverRules:
    """How a league hands out players (ADR-046). Platforms map their settings onto this."""

    kind: WaiverKind
    budget: int | None = None  # FAAB budget per team; None unless kind == "faab"
    min_bid: int = 0
    # Days a dropped player stays on waivers before becoming a free agent.
    clear_days: int = 0
    # Day of the week waivers run (0 = Monday ... 6 = Sunday), None if not weekly.
    weekly_day: int | None = None
    # Daily waivers: unclaimed players clear every day at `daily_hour` (league's local hour).
    daily: bool = False
    daily_hour: int | None = None
    # The platform's raw values, kept so an unclear mapping can be checked later.
    raw: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class SeasonRules:
    kind: LeagueKind = "redraft"
    start_week: int = 1
    playoff_week_start: int | None = None  # first fantasy playoff week; None = no playoffs
    playoff_teams: int | None = None
    # one_week: one week per round · two_week_final: the final spans two weeks ·
    # two_week_rounds: every round spans two weeks
    playoff_round: PlayoffRound = "one_week"
    trade_deadline: int | None = None  # last week trades are allowed; None = no deadline
    trades_allowed: bool = True


@dataclass(frozen=True)
class LeagueData:
    ref: LeagueRef
    avatar_url: str | None
    # Platform rule name -> points. Interpreted by app/model/scoring.py for this platform.
    scoring_rules: dict[str, float]
    # One entry per lineup position in order, e.g. ["QB","RB","RB",...,"BN","BN"].
    roster_slots: list[str]
    status: str  # pre_draft / drafting / in_season / complete
    waivers: WaiverRules = field(default_factory=lambda: WaiverRules("none"))
    season_rules: SeasonRules = field(default_factory=SeasonRules)


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
    waiver_position: int | None = None  # claim order; 1 = first
    waiver_budget_used: int | None = None  # FAAB spent so far


@dataclass(frozen=True)
class MatchupData:
    week: int
    matchup_key: str | None  # teams sharing a key play each other; None = bye/no opponent
    team_external_id: str
    points: float | None
    # Starters actually set for that week (historical weeks), in slot order.
    roster: list[RosterSpot] = field(default_factory=list)
    # Fantasy points so far per player, scored by the platform with the league's rules.
    player_points: dict[str, float] = field(default_factory=dict)


TransactionKind = Literal["waiver", "free_agent", "trade", "commissioner"]


@dataclass(frozen=True)
class TransactionData:
    external_id: str
    kind: TransactionKind
    status: str  # complete / failed / pending
    week: int
    created_at: datetime
    # player external id -> team external id
    adds: dict[str, str] = field(default_factory=dict)
    drops: dict[str, str] = field(default_factory=dict)
    waiver_bid: int | None = None


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
    async def fetch_transactions(self, league: LeagueData, week: int) -> list[TransactionData]: ...
    async def fetch_players(self) -> list[PlayerData]: ...
    async def fetch_state(self) -> NflState: ...
