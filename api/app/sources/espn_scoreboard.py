"""The ONLY module that reads ESPN's public NFL scoreboard (ADR-044).

Used for game state during live games: quarter, clock, possession, final. Fantasy points come
from Sleeper, never from here. The feed is public but unofficial, so its shape is checked on
every load (schema contract, like app/sources/nflverse.py): a missing required field raises
`ScoreboardSchemaError`, and callers fall back to points-only win chance (nothing else breaks).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.config import get_settings
from app.nfl_teams import canonical_team

GameState = Literal["upcoming", "in_progress", "halftime", "final", "postponed"]

QUARTER_SECONDS = 15 * 60
REGULATION_SECONDS = 4 * QUARTER_SECONDS
REGULAR_SEASON = 2


class ScoreboardError(Exception):
    """The scoreboard couldn't be reached (retry later; live win chance uses points only)."""


class ScoreboardSchemaError(ScoreboardError):
    """The scoreboard's response no longer has the shape we expect."""


# --------------------------------------------------------------------------- raw shapes
class _Raw(BaseModel):
    model_config = ConfigDict(extra="ignore")


class _StatusType(_Raw):
    name: str
    state: str  # pre / in / post
    completed: bool = False
    shortDetail: str | None = None


class _Status(_Raw):
    clock: float = 0.0
    displayClock: str = "0:00"
    period: int = 0
    type: _StatusType


class _Team(_Raw):
    id: str
    abbreviation: str


class _Competitor(_Raw):
    id: str
    homeAway: str
    score: str | None = None
    team: _Team


class _Situation(_Raw):
    possession: str | None = None  # the competitor (team) id with the ball


class _Competition(_Raw):
    competitors: list[_Competitor]
    status: _Status | None = None
    situation: _Situation | None = None


class _Event(_Raw):
    id: str
    date: datetime
    status: _Status
    competitions: list[_Competition]


class _Week(_Raw):
    number: int


class _Season(_Raw):
    year: int
    type: int


class _Scoreboard(_Raw):
    season: _Season
    week: _Week
    events: list[_Event]


# --------------------------------------------------------------------------- clean output
@dataclass(frozen=True)
class GameStatus:
    espn_id: str
    season: int
    week: int
    home: str  # our team codes (app/nfl_teams.py)
    away: str
    kickoff_at: datetime
    state: GameState
    period: int  # 1-4, 5+ = overtime; 0 before kickoff
    clock_seconds: float  # left in the period
    detail: str  # ESPN's short text, e.g. "4:12 - 3rd", "Halftime", "Final"
    home_score: int | None
    away_score: int | None
    possession: str | None  # team code with the ball, while in progress

    @property
    def remaining_fraction(self) -> float:
        """Share of the game still to play: 1 before kickoff, 0 when final (ADR-044)."""
        if self.state in ("upcoming", "postponed"):
            return 1.0
        if self.state == "final":
            return 0.0
        if self.state == "halftime":
            return 0.5
        if self.period > 4:  # overtime: little left, whatever the clock says
            return 0.0
        left = (4 - self.period) * QUARTER_SECONDS + max(0.0, self.clock_seconds)
        return max(0.0, min(1.0, left / REGULATION_SECONDS))


def _state(t: _StatusType) -> GameState:
    name = t.name.upper()
    if "POSTPONED" in name or "CANCELED" in name:
        return "postponed"
    if name == "STATUS_HALFTIME":
        return "halftime"
    if t.state == "post" or t.completed:
        return "final"
    if t.state == "in":
        return "in_progress"
    return "upcoming"


def _score(raw: str | None) -> int | None:
    try:
        return int(raw) if raw not in (None, "") else None
    except ValueError:
        return None


def parse_scoreboard(data: Any) -> list[GameStatus]:
    """ESPN's scoreboard JSON -> one GameStatus per game. Raises ScoreboardSchemaError."""
    try:
        sb = _Scoreboard.model_validate(data)
    except ValidationError as exc:
        raise ScoreboardSchemaError(f"ESPN scoreboard changed shape: {exc}") from exc

    games = []
    for e in sb.events:
        if not e.competitions:
            raise ScoreboardSchemaError(f"ESPN event {e.id} has no competition")
        comp = e.competitions[0]
        sides = {c.homeAway: c for c in comp.competitors}
        if set(sides) != {"home", "away"}:
            raise ScoreboardSchemaError(f"ESPN event {e.id} lacks a home or away team")
        status = comp.status or e.status
        home, away = sides["home"], sides["away"]
        state = _state(status.type)
        with_ball = comp.situation.possession if comp.situation else None
        team_by_id = {home.id: home.team.abbreviation, away.id: away.team.abbreviation}
        home_code, away_code = (
            canonical_team(home.team.abbreviation),
            canonical_team(away.team.abbreviation),
        )
        assert home_code and away_code
        games.append(
            GameStatus(
                espn_id=e.id,
                season=sb.season.year,
                week=sb.week.number,
                home=home_code,
                away=away_code,
                kickoff_at=e.date,
                state=state,
                period=status.period,
                clock_seconds=status.clock,
                detail=status.type.shortDetail or status.displayClock,
                home_score=_score(home.score) if state != "upcoming" else None,
                away_score=_score(away.score) if state != "upcoming" else None,
                possession=canonical_team(team_by_id.get(with_ball or ""))
                if state == "in_progress"
                else None,
            )
        )
    return games


async def fetch_week(
    season: int,
    week: int,
    *,
    client: httpx.AsyncClient | None = None,
    season_type: int = REGULAR_SEASON,
) -> list[GameStatus]:
    """Every game of one NFL week, as it stands now."""
    own = client is None
    http = client or httpx.AsyncClient(
        base_url=get_settings().espn_scoreboard_url,
        timeout=httpx.Timeout(10.0, connect=5.0),
        headers={"User-Agent": "SundayWarRoom/0.1"},
    )
    try:
        resp = await http.get(
            "/scoreboard", params={"seasontype": season_type, "week": week, "dates": season}
        )
    except httpx.TransportError as exc:
        raise ScoreboardError(f"ESPN scoreboard unreachable: {exc}") from exc
    finally:
        if own:
            await http.aclose()
    if resp.status_code != 200:
        raise ScoreboardError(f"ESPN scoreboard -> HTTP {resp.status_code}")
    return parse_scoreboard(resp.json())
