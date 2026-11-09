"""Sleeper adapter: the only module that knows Sleeper's URLs and JSON shapes.

Sleeper's API is public and read-only (no login): https://docs.sleeper.com
Raw responses are validated with pydantic models below. A missing *required* field raises
AdapterSchemaError (fail loudly); optional fields default to None (fail softly).
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from app.adapters.base import (
    BENCH,
    IR,
    STARTER_SLOTS,
    TAXI,
    AdapterError,
    AdapterSchemaError,
    LeagueData,
    LeagueRef,
    MatchupData,
    NflState,
    NotFoundOnPlatform,
    Platform,
    PlatformUser,
    PlayerData,
    RosterSpot,
    TeamData,
)

BASE_URL = "https://api.sleeper.app/v1"
AVATAR_URL = "https://sleepercdn.com/avatars/thumbs/{}"
# Sleeper marks an empty starting slot with "0".
EMPTY_SLOT = "0"
FANTASY_POSITIONS = {"QB", "RB", "WR", "TE", "K", "DEF"}


# --------------------------------------------------------------------------- raw shapes
class _Raw(BaseModel):
    model_config = ConfigDict(extra="ignore")


class _User(_Raw):
    user_id: str
    username: str | None = None
    display_name: str | None = None


class _League(_Raw):
    league_id: str
    name: str
    season: str
    status: str
    avatar: str | None = None
    total_rosters: int | None = None
    scoring_settings: dict[str, float]
    roster_positions: list[str]


class _LeagueUser(_Raw):
    user_id: str
    display_name: str | None = None
    avatar: str | None = None
    metadata: dict[str, Any] | None = None


class _RosterSettings(_Raw):
    wins: int = 0
    losses: int = 0
    ties: int = 0


class _Roster(_Raw):
    roster_id: int
    owner_id: str | None = None
    players: list[str] | None = None
    starters: list[str] | None = None
    reserve: list[str] | None = None
    taxi: list[str] | None = None
    settings: _RosterSettings


class _Matchup(_Raw):
    roster_id: int
    matchup_id: int | None = None
    points: float | None = None
    starters: list[str] | None = None
    players: list[str] | None = None


class _Player(_Raw):
    player_id: str
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    position: str | None = None
    fantasy_positions: list[str] | None = None
    team: str | None = None
    status: str | None = None
    injury_status: str | None = None
    gsis_id: str | None = None
    espn_id: int | str | None = None
    yahoo_id: int | str | None = None
    depth_chart_order: int | None = None


class _State(_Raw):
    season: str
    week: int
    season_type: str


def _parse(model: Any, data: Any, what: str) -> Any:
    try:
        return TypeAdapter(model).validate_python(data)
    except ValidationError as exc:
        raise AdapterSchemaError(f"Sleeper {what} response changed shape: {exc}") from exc


# --------------------------------------------------------------------------- adapter
class SleeperAdapter:
    platform: Platform = "sleeper"

    def __init__(self, client: httpx.AsyncClient | None = None, *, retries: int = 3) -> None:
        self._client = client or httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=httpx.Timeout(20.0, connect=5.0),
            headers={"User-Agent": "SundayWarRoom/0.1"},
        )
        self._retries = retries

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str) -> Any:
        """GET with small retries on network errors, 429 and 5xx. Returns parsed JSON."""
        delay = 0.5
        for attempt in range(self._retries + 1):
            try:
                resp = await self._client.get(path)
            except httpx.TransportError as exc:
                if attempt == self._retries:
                    raise AdapterError(f"Sleeper unreachable: {exc}") from exc
            else:
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code == 404:
                    raise NotFoundOnPlatform(path)
                if resp.status_code not in (429, 500, 502, 503, 504) or attempt == self._retries:
                    raise AdapterError(f"Sleeper {path} -> HTTP {resp.status_code}")
            await asyncio.sleep(delay)
            delay *= 2
        raise AssertionError("unreachable")

    # -- users & leagues -------------------------------------------------------
    async def find_user(self, username: str) -> PlatformUser:
        data = await self._get(f"/user/{username.strip()}")
        if data is None:  # Sleeper answers 200 + null for unknown usernames
            raise NotFoundOnPlatform(f"Sleeper user {username!r}")
        u: _User = _parse(_User, data, "user")
        return PlatformUser(
            external_user_id=u.user_id,
            username=u.username or username,
            display_name=u.display_name or u.username or username,
        )

    async def find_leagues(self, user: PlatformUser, season: int) -> list[LeagueRef]:
        data = await self._get(f"/user/{user.external_user_id}/leagues/nfl/{season}") or []
        leagues: list[_League] = _parse(list[_League], data, "user leagues")
        return [
            LeagueRef("sleeper", lg.league_id, int(lg.season), lg.name, lg.total_rosters)
            for lg in leagues
        ]

    async def fetch_league(self, external_id: str) -> LeagueData:
        data = await self._get(f"/league/{external_id}")
        if data is None:
            raise NotFoundOnPlatform(f"Sleeper league {external_id}")
        lg: _League = _parse(_League, data, "league")
        return LeagueData(
            ref=LeagueRef("sleeper", lg.league_id, int(lg.season), lg.name, lg.total_rosters),
            avatar_url=AVATAR_URL.format(lg.avatar) if lg.avatar else None,
            scoring_rules=dict(lg.scoring_settings),
            roster_slots=list(lg.roster_positions),
            status=lg.status,
        )

    # -- teams -----------------------------------------------------------------
    async def fetch_teams(self, league: LeagueData) -> list[TeamData]:
        lid = league.ref.external_id
        rosters_raw, users_raw = await asyncio.gather(
            self._get(f"/league/{lid}/rosters"), self._get(f"/league/{lid}/users")
        )
        rosters: list[_Roster] = _parse(list[_Roster], rosters_raw or [], "rosters")
        users: dict[str, _LeagueUser] = {
            u.user_id: u for u in _parse(list[_LeagueUser], users_raw or [], "league users")
        }

        teams = []
        for r in rosters:
            owner = users.get(r.owner_id) if r.owner_id else None
            team_name = (owner.metadata or {}).get("team_name") if owner else None
            owner_name = owner.display_name if owner else None
            teams.append(
                TeamData(
                    external_id=str(r.roster_id),
                    owner_external_id=r.owner_id,
                    name=team_name or owner_name or f"Team {r.roster_id}",
                    owner_name=owner_name,
                    avatar_url=AVATAR_URL.format(owner.avatar) if owner and owner.avatar else None,
                    wins=r.settings.wins,
                    losses=r.settings.losses,
                    ties=r.settings.ties,
                    roster=build_roster(
                        league.roster_slots, r.starters, r.players, r.reserve, r.taxi
                    ),
                )
            )
        return teams

    async def fetch_matchups(self, league: LeagueData, week: int) -> list[MatchupData]:
        data = await self._get(f"/league/{league.ref.external_id}/matchups/{week}") or []
        rows: list[_Matchup] = _parse(list[_Matchup], data, "matchups")
        return [
            MatchupData(
                week=week,
                matchup_key=str(m.matchup_id) if m.matchup_id is not None else None,
                team_external_id=str(m.roster_id),
                points=m.points,
                roster=build_roster(league.roster_slots, m.starters, m.players, None, None),
            )
            for m in rows
        ]

    # -- NFL-wide --------------------------------------------------------------
    async def fetch_players(self) -> list[PlayerData]:
        """Every NFL player Sleeper knows (~5 MB). Call at most once a day (Sleeper's ask).

        Sleeper's own gsis_id/espn_id fields are sparse (most players lack them), so they are
        only a fallback: the authoritative crosswalk comes from nflverse (app/sources/nflverse.py).
        """
        data = await self._get("/players/nfl")
        if not isinstance(data, dict) or not data:
            raise AdapterSchemaError("Sleeper players response is not a non-empty object")
        out = []
        for pid, raw in data.items():
            p: _Player = _parse(
                _Player, {**raw, "player_id": raw.get("player_id") or pid}, "player"
            )
            position = fantasy_position(p.position, p.fantasy_positions)
            if position is None:
                continue
            name = p.full_name or " ".join(x for x in (p.first_name, p.last_name) if x) or pid
            out.append(
                PlayerData(
                    external_id=p.player_id,
                    name=name,
                    position=position,
                    nfl_team=p.team,
                    status=p.status,
                    injury_status=p.injury_status,
                    gsis_id=(p.gsis_id or "").strip() or None,
                    espn_id=str(p.espn_id) if p.espn_id else None,
                    yahoo_id=str(p.yahoo_id) if p.yahoo_id else None,
                    depth_chart_order=p.depth_chart_order,
                )
            )
        return out

    async def fetch_state(self) -> NflState:
        s: _State = _parse(_State, await self._get("/state/nfl"), "state")
        return NflState(season=int(s.season), week=s.week, season_type=s.season_type)


def fantasy_position(position: str | None, eligible: list[str] | None) -> str | None:
    """The position a player is scored at, or None if they can't be started in fantasy.

    Usually `position`; for two-way players (e.g. listed "DB" but WR-eligible) it's the first
    fantasy-eligible position Sleeper lists.
    """
    if position in FANTASY_POSITIONS:
        return position
    return next((p for p in eligible or [] if p in FANTASY_POSITIONS), None)


def build_roster(
    roster_slots: list[str],
    starters: list[str] | None,
    players: list[str] | None,
    reserve: list[str] | None,
    taxi: list[str] | None,
) -> list[RosterSpot]:
    """Turn Sleeper's parallel lists into slot assignments.

    `starters` lines up with the non-bench entries of `roster_positions`; "0" is an empty slot.
    Everyone else on the roster is bench, IR (reserve) or taxi.
    """
    starter_slots = [s for s in roster_slots if s in STARTER_SLOTS]
    spots: list[RosterSpot] = []
    starters = starters or []
    if len(starters) > len(starter_slots):
        raise AdapterSchemaError(
            f"{len(starters)} starters but only {len(starter_slots)} starting slots"
        )
    for slot, pid in zip(starter_slots, starters, strict=False):
        if pid and pid != EMPTY_SLOT:
            spots.append(RosterSpot(pid, slot, True))

    placed = {s.player_external_id for s in spots}
    for pid in reserve or []:
        if pid not in placed:
            spots.append(RosterSpot(pid, IR, False))
            placed.add(pid)
    for pid in taxi or []:
        if pid not in placed:
            spots.append(RosterSpot(pid, TAXI, False))
            placed.add(pid)
    for pid in players or []:
        if pid not in placed:
            spots.append(RosterSpot(pid, BENCH, False))
            placed.add(pid)
    return spots
