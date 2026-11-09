"""Response/request shapes: these become the OpenAPI schema and the generated TS client."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorOut(Schema):
    """Every error the API returns has this shape (app/errors.py)."""

    detail: str
    code: str  # stable machine-readable code, e.g. league_not_found, rate_limited


class MembershipOut(Schema):
    league_id: int
    league_name: str
    platform: str
    season: int
    my_team_id: int | None
    last_synced_at: datetime | None


class MeOut(Schema):
    id: int
    email: str | None
    name: str | None
    image: str | None
    plan: str
    sleeper_username: str | None
    memberships: list[MembershipOut]


class JobAccepted(Schema):
    job_id: str
    status: str


class JobOut(Schema):
    job_id: str
    kind: str
    status: str  # queued / running / done / failed
    league_id: int | None
    error: str | None
    result: dict[str, Any] | None
    created_at: datetime
    finished_at: datetime | None


class SleeperConnectIn(BaseModel):
    username: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.\-]+$")


class FollowLeagueIn(BaseModel):
    platform: Literal["sleeper"]
    external_id: str = Field(pattern=r"^\d{1,32}$")


class LeagueOut(Schema):
    id: int
    platform: str
    external_id: str
    season: int
    name: str
    avatar_url: str | None
    current_week: int | None
    my_team_id: int | None
    last_synced_at: datetime | None
    sync_status: str | None  # status of the newest sync run


class FollowLeagueOut(Schema):
    league: LeagueOut
    job_id: str


class SetMyTeamIn(BaseModel):
    my_team_id: int


class TeamOut(Schema):
    id: int
    name: str
    owner_name: str | None
    avatar_url: str | None
    wins: int
    losses: int
    ties: int


# --------------------------------------------------------------------------- projections & views
class Factor(Schema):
    name: str  # baseline / opponent / role / depth / injury / bye
    value: float
    effect: float  # points this step added (+) or removed (-)
    note: str


class ProjectionOut(Schema):
    points: float
    p10: float
    p50: float
    p90: float
    frozen: bool
    computed_at: datetime
    model_version: str


class PlayerLine(Schema):
    player_id: int
    name: str
    position: str | None
    nfl_team: str | None
    headshot_url: str | None
    slot: str
    injury_status: str | None
    opponent: str | None  # "@KC" / "vs KC"; None = bye
    kickoff_at: datetime | None
    game_status: Literal["upcoming", "in_progress", "final", "bye"]
    projection: ProjectionOut | None
    actual_points: float | None  # final games only (nflverse)


class TeamSide(Schema):
    team_id: int
    name: str
    owner_name: str | None
    avatar_url: str | None
    record: str
    score: float | None  # as of the last Sleeper sync
    projected_total: float  # final games' actual points + everyone else's projection
    starters: list[PlayerLine]


class WinOutlook(Schema):
    win_probability: float  # my chance, 0-1
    my_median: float
    opponent_median: float
    my_range: tuple[float, float]  # p10, p90 of my total
    opponent_range: tuple[float, float]


class MatchupOut(Schema):
    league_id: int
    week: int
    as_of: datetime | None
    model_version: str
    me: TeamSide
    opponent: TeamSide | None  # None = no opponent this week
    outlook: WinOutlook | None
    unsupported_rules: list[str]


class SwapOut(Schema):
    slot: str
    player_in: PlayerLine
    player_out: PlayerLine | None
    gain: float


class LineupOut(Schema):
    league_id: int
    week: int
    as_of: datetime | None
    model_version: str
    starters: list[PlayerLine]
    bench: list[PlayerLine]
    optimal: list[tuple[str, int | None]]  # (slot, player_id) in league slot order
    swaps: list[SwapOut]
    current_points: float
    optimal_points: float
    win_probability_current: float | None
    win_probability_optimal: float | None


class GameLine(Schema):
    week: int
    opponent: str | None
    points: float


class PlayerProjectionOut(Schema):
    player: PlayerLine
    factors: list[Factor]
    recent_games: list[GameLine]  # this season, scored with the league's rules
    unsupported_rules: list[str]


class AccuracyWeek(Schema):
    week: int
    n: int
    mae: float
    coverage_80: float


class AccuracyOut(Schema):
    league_id: int
    model_version: str
    n: int
    mae: float | None
    bias: float | None
    coverage_80: float | None
    by_position: dict[str, dict[str, float]]
    weeks: list[AccuracyWeek]
