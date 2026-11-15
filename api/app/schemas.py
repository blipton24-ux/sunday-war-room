"""Response/request shapes: these become the OpenAPI schema and the generated TS client."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr


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


class PlatformOut(Schema):
    """A connected platform account. Never carries the stored credentials."""

    platform: str  # sleeper / espn / yahoo
    display_name: str | None
    # ok / pending (just saved, not yet checked) / needs_reconnect (the platform refused them)
    status: str


class MeOut(Schema):
    id: int
    email: str | None
    name: str | None
    image: str | None
    plan: str
    sleeper_username: str | None
    platforms: list[PlatformOut]
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


class EspnProbeIn(BaseModel):
    """A pasted league link (or just the league id): is the league public?"""

    link: str = Field(min_length=1, max_length=500)


class EspnCredentialsIn(BaseModel):
    """The two ESPN cookies (ADR-051). SecretStr keeps them out of validation-error echoes."""

    espn_s2: SecretStr = Field(min_length=20, max_length=2000)
    swid: SecretStr = Field(min_length=36, max_length=60)


class FollowLeagueIn(BaseModel):
    platform: Literal["sleeper", "espn"]
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
    # True when this user's own platform cookies were refused: reconnect to see the league.
    needs_reconnect: bool = False


class FollowLeagueOut(Schema):
    league: LeagueOut
    job_id: str


class SetMyTeamIn(BaseModel):
    my_team_id: int


class TeamOut(Schema):
    id: int
    # The platform's own id for the team (ESPN's team id): lets onboarding preselect the team ESPN
    # says is the user's.
    external_id: str
    name: str
    owner_name: str | None
    # The platform's user id of the owner: lets onboarding pre-select the user's own team.
    owner_external_id: str | None
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
    # Final games: nflverse stats when published, else the platform's points (P2 live).
    actual_points: float | None
    # P2 live game day (ADR-044): points so far from the platform, ESPN's game state.
    live_points: float | None = None
    game_detail: str | None = None  # e.g. "4:12 - 3rd", "Halftime"
    has_ball: bool = False
    remaining_fraction: float | None = None  # share of his game still to play


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
    # P2 live game day: any starter's game in progress; screens poll while this is true.
    live: bool = False
    # Where "time left" comes from: ESPN's game clock, or (if it's down) kickoff time.
    clock_source: Literal["scoreboard", "kickoff_estimate"] | None = None
    scores_updated_at: datetime | None = None


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


# --------------------------------------------------------------------------- P2: waivers
class PlayerRef(Schema):
    player_id: int
    name: str
    position: str | None
    nfl_team: str | None
    headshot_url: str | None
    injury_status: str | None


class WaiverPlayer(Schema):
    player: PlayerRef
    gain: float  # weighted points my best lineup gains over the horizon, after the drop
    gain_per_week: float
    points_per_week: float  # the player's own projection, averaged over the horizon
    status: Literal["free_agent", "waivers"]
    on_waivers_until: datetime | None  # approximate; platforms run waivers at set times
    drop: PlayerRef | None  # who to drop to make room (None: an open roster spot)
    bid_low: int | None  # FAAB leagues only: a guide, not a prediction
    bid_high: int | None


class WaiversOut(Schema):
    league_id: int
    week: int
    horizon: Literal["ros", "week"]
    horizon_weeks: list[int]
    playoff_weeks: list[int]
    waiver_kind: Literal["rolling", "reverse_standings", "faab", "none"]
    faab_budget: int | None
    faab_remaining: int | None
    my_waiver_position: int | None  # 1 = first claim
    clear_days: int
    players: list[WaiverPlayer]
    ready: bool  # False until the worker has projected this league's free agents


# --------------------------------------------------------------------------- P2: trades
class RosterPlayer(Schema):
    player: PlayerRef
    slot: str  # where he sits now: a starting slot, BN, IR or TAXI
    points_per_week: float  # rest-of-season projection, averaged over the horizon


class TradeTeam(Schema):
    team_id: int
    name: str
    owner_name: str | None
    avatar_url: str | None
    is_mine: bool
    players: list[RosterPlayer]


class TradeRostersOut(Schema):
    league_id: int
    week: int
    horizon_weeks: list[int]
    league_kind: Literal["redraft", "keeper", "dynasty"]  # dynasty/keeper: this-season value only
    trades_allowed: bool
    trade_deadline: int | None
    deadline_passed: bool
    teams: list[TradeTeam]
    ready: bool


class TradeEvaluateIn(BaseModel):
    team_a_id: int
    team_b_id: int
    a_gives: list[int]  # player ids from team A
    b_gives: list[int]  # player ids from team B


class LineupSlot(Schema):
    slot: str
    player: PlayerRef | None
    points_per_week: float


class TradeSideOut(Schema):
    team_id: int
    name: str
    gives: list[PlayerRef]
    gets: list[PlayerRef]
    before_per_week: float  # best-lineup points per week over the rest of the season
    after_per_week: float
    change_per_week: float
    dropped: list[PlayerRef]  # who this team would have to drop to fit its roster
    lineup_before: list[LineupSlot]
    lineup_after: list[LineupSlot]


class TradeEvaluationOut(Schema):
    league_id: int
    horizon_weeks: list[int]
    a: TradeSideOut
    b: TradeSideOut


class TradeIdeaOut(Schema):
    other_team_id: int
    other_team_name: str
    gives: list[PlayerRef]  # mine
    gets: list[PlayerRef]  # theirs
    my_change_per_week: float
    their_change_per_week: float


class TradeSuggestionsOut(Schema):
    league_id: int
    max_loss_per_week: float
    ideas: list[TradeIdeaOut]
    ready: bool
