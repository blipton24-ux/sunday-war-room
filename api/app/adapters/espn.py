"""ESPN adapter: the only module that knows ESPN's URLs, cookies and JSON shapes (ADR-053).

ESPN's fantasy API is unofficial. A private league answers only to the two cookies a signed-in
browser holds (ADR-051): `SWID` (which account) and `espn_s2` (proof of sign-in). They are passed
in per request, never stored on the shared HTTP client, so one client serves every user.

Like the Sleeper adapter, raw responses are validated with pydantic models: a missing *required*
field raises AdapterSchemaError (fail loudly, never score on a guess); optional fields default.
Anything ESPN omits on purpose (a zero scoring rule) is handled in app/model/scoring_espn.py.

Not built from ESPN documentation (there is none): the shapes below come from earlier work and are
checked against the owner's real league in Verification Gaps (P3 step 15).
"""

from __future__ import annotations

import asyncio
import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from app.adapters.base import (
    BENCH,
    IR,
    AdapterError,
    AdapterSchemaError,
    AuthRequired,
    CredentialsInvalid,
    LeagueData,
    LeagueRef,
    MatchupData,
    NotFoundOnPlatform,
    Platform,
    PlayerHint,
    PlayoffRound,
    RosterSpot,
    SeasonRules,
    TeamData,
    TransactionData,
    TransactionKind,
    UnsupportedLeague,
    WaiverKind,
    WaiverRules,
)
from app.adapters.espn_teams import team_for_pro_team_id
from app.config import get_settings
from app.model.scoring_espn import expand_espn

# ESPN's lineup slot id -> our slot. Slots for positions we don't project (individual defenders,
# punters, head coaches, ...) are absent on purpose: those players are treated as bench.
_SLOTS: dict[int, str] = {
    0: "QB",
    2: "RB",
    4: "WR",
    6: "TE",
    23: "FLEX",  # RB / WR / TE
    3: "WRRB_FLEX",  # RB / WR
    5: "REC_FLEX",  # WR / TE
    7: "SUPER_FLEX",  # "OP": QB / RB / WR / TE
    17: "K",
    16: "DEF",
    20: BENCH,
    21: IR,
}
_SLOT_ORDER = [0, 2, 4, 6, 23, 3, 5, 7, 17, 16, 20, 21]  # how roster_slots is listed
# ESPN's defaultPositionId -> our position
_POSITIONS: dict[int, str] = {1: "QB", 2: "RB", 3: "WR", 4: "TE", 5: "K", 16: "DEF"}
_STARTING = {s for s in _SLOTS.values() if s not in (BENCH, IR)}
_WEEKDAYS = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}
_SWID = re.compile(r"^\{?([0-9A-Fa-f-]{36})\}?$")


# --------------------------------------------------------------------------- credentials
@dataclass(frozen=True)
class EspnCredentials:
    """The two cookies that identify a signed-in ESPN user. Treat like a password."""

    espn_s2: str
    swid: str

    def __repr__(self) -> str:  # never let a stray log line or traceback print the secrets
        return "EspnCredentials(<redacted>)"

    def to_json(self) -> str:
        return json.dumps({"espn_s2": self.espn_s2, "swid": self.swid})

    @classmethod
    def from_json(cls, text: str) -> EspnCredentials:
        data = json.loads(text)
        return cls(espn_s2=data["espn_s2"], swid=data["swid"])


@dataclass(frozen=True)
class EspnAccess:
    """What a worker needs to read one user's leagues: the season and (for private ones) cookies."""

    season: int
    credentials: EspnCredentials | None = None


def normalize_swid(value: str) -> str:
    """`SWID` as ESPN sends it: upper-case GUID in braces. Accepts it with or without them."""
    m = _SWID.match(value.strip().strip("\"'"))
    if not m:
        raise ValueError("SWID should look like {XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}")
    return "{" + m.group(1).upper() + "}"


def make_credentials(espn_s2: str, swid: str) -> EspnCredentials:
    """Validate and tidy pasted cookies. The espn_s2 value is kept exactly as the browser has it."""
    s2 = espn_s2.strip().strip("\"'")
    if len(s2) < 20 or any(c.isspace() or c == ";" for c in s2):
        raise ValueError("espn_s2 doesn't look right: paste the whole value, with no spaces")
    return EspnCredentials(espn_s2=s2, swid=normalize_swid(swid))


@dataclass(frozen=True)
class EspnLeagueLink:
    league_id: str
    season: int | None
    team_id: str | None


_LINK_ID = re.compile(r"leagueId=(\d+)")
_LINK_SEASON = re.compile(r"seasonId=(\d{4})")
_LINK_TEAM = re.compile(r"teamId=(\d+)")


def parse_league_link(text: str) -> EspnLeagueLink:
    """A league id from what a user pastes: the whole URL, or just the number."""
    text = text.strip()
    if text.isdigit():
        return EspnLeagueLink(text, None, None)
    m = _LINK_ID.search(text)
    if not m:
        raise ValueError("Paste your ESPN league link (it contains leagueId=...) or the league id")
    season, team = _LINK_SEASON.search(text), _LINK_TEAM.search(text)
    return EspnLeagueLink(
        m.group(1), int(season.group(1)) if season else None, team.group(1) if team else None
    )


# --------------------------------------------------------------------------- raw shapes
class _Raw(BaseModel):
    model_config = ConfigDict(extra="ignore")


class _Player(_Raw):
    id: int | None = None
    fullName: str | None = None
    defaultPositionId: int | None = None
    proTeamId: int | None = None
    injuryStatus: str | None = None


class _PoolEntry(_Raw):
    appliedStatTotal: float | None = None
    player: _Player | None = None


class _Entry(_Raw):
    playerId: int
    lineupSlotId: int
    playerPoolEntry: _PoolEntry | None = None


class _RosterBlock(_Raw):
    entries: list[_Entry] = Field(default_factory=list)


class _Overall(_Raw):
    wins: int = 0
    losses: int = 0
    ties: int = 0


class _Record(_Raw):
    overall: _Overall = _Overall()


class _Counter(_Raw):
    acquisitionBudgetSpent: int | None = None


class _Team(_Raw):
    id: int
    name: str | None = None
    location: str | None = None
    nickname: str | None = None
    abbrev: str | None = None
    primaryOwner: str | None = None
    owners: list[str] = Field(default_factory=list)
    logo: str | None = None
    waiverRank: int | None = None
    record: _Record = _Record()
    transactionCounter: _Counter = _Counter()
    roster: _RosterBlock | None = None


class _Member(_Raw):
    id: str
    displayName: str | None = None
    firstName: str | None = None
    lastName: str | None = None


class _ScoringSettings(_Raw):
    scoringType: str | None = None
    scoringItems: list[dict[str, Any]]


class _RosterSettings(_Raw):
    lineupSlotCounts: dict[str, int]


class _Schedule(_Raw):
    matchupPeriodCount: int | None = None
    matchupPeriods: dict[str, list[int]] = Field(default_factory=dict)
    playoffTeamCount: int | None = None
    playoffMatchupPeriodLength: int | None = None


class _Acquisition(_Raw):
    acquisitionType: str | None = None
    isUsingAcquisitionBudget: bool | None = None
    acquisitionBudget: int | None = None
    minimumBid: int | None = None
    waiverHours: int | None = None
    waiverOrderReset: bool | None = None
    waiverProcessDays: list[str] = Field(default_factory=list)


class _Settings(_Raw):
    name: str
    size: int | None = None
    isPublic: bool | None = None
    scoringSettings: _ScoringSettings
    rosterSettings: _RosterSettings
    scheduleSettings: _Schedule = _Schedule()
    acquisitionSettings: _Acquisition = _Acquisition()


class _Status(_Raw):
    isActive: bool | None = None
    currentMatchupPeriod: int | None = None
    firstScoringPeriod: int | None = None


class _LeagueDoc(_Raw):
    id: int
    seasonId: int | None = None
    scoringPeriodId: int | None = None
    status: _Status = _Status()
    settings: _Settings
    teams: list[_Team] = Field(default_factory=list)
    members: list[_Member] = Field(default_factory=list)


class _Side(_Raw):
    teamId: int
    totalPoints: float | None = None
    pointsByScoringPeriod: dict[str, float] = Field(default_factory=dict)
    rosterForCurrentScoringPeriod: _RosterBlock | None = None
    rosterForMatchupPeriod: _RosterBlock | None = None


class _ScheduleItem(_Raw):
    id: int | None = None
    matchupPeriodId: int
    home: _Side
    away: _Side | None = None  # a bye has no opponent


class _MatchupDoc(_Raw):
    settings: _Settings
    status: _Status = _Status()
    schedule: list[_ScheduleItem] = Field(default_factory=list)


class _TxItem(_Raw):
    playerId: int
    type: str
    fromTeamId: int | None = None
    toTeamId: int | None = None


class _Transaction(_Raw):
    id: str
    type: str
    status: str | None = None
    scoringPeriodId: int | None = None
    proposedDate: int | None = None
    bidAmount: int | None = None
    teamId: int | None = None
    items: list[_TxItem] = Field(default_factory=list)


class _TransactionDoc(_Raw):
    transactions: list[_Transaction] = Field(default_factory=list)


class _FanGroup(_Raw):
    groupId: int | str
    groupName: str | None = None


class _FanEntry(_Raw):
    gameId: int | None = None
    seasonId: int | None = None
    entryId: int | None = None
    groups: list[_FanGroup] = Field(default_factory=list)
    entryLocation: str | None = None
    entryNickname: str | None = None


class _FanMeta(_Raw):
    entry: _FanEntry | None = None


class _FanPreference(_Raw):
    metaData: _FanMeta | None = None


class _FanDoc(_Raw):
    preferences: list[_FanPreference] = Field(default_factory=list)


def _parse(model: Any, data: Any, what: str) -> Any:
    try:
        return TypeAdapter(model).validate_python(data)
    except ValidationError as exc:
        raise AdapterSchemaError(f"ESPN {what} response changed shape: {exc}") from exc


# --------------------------------------------------------------------------- HTTP
FOOTBALL = 1  # ESPN's gameId for fantasy football


class EspnHttp:
    """One HTTP client for every user; cookies ride on each request (never on the client)."""

    def __init__(self, client: httpx.AsyncClient | None = None, *, retries: int = 3) -> None:
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=5.0),
            headers={"User-Agent": "SundayWarRoom/0.1", "Accept": "application/json"},
        )
        self._retries = retries

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(
        self,
        url: str,
        params: list[tuple[str, str | int | float | bool | None]] | None = None,
        credentials: EspnCredentials | None = None,
        *,
        what: str = "request",
    ) -> Any:
        """GET with retries on network errors, 429 and 5xx. Returns parsed JSON.

        401/403 with cookies means they no longer work (CredentialsInvalid); without cookies it
        means the league is private (AuthRequired); 404 is an unknown league or season.
        """
        headers = {}
        if credentials is not None:
            headers["Cookie"] = f"espn_s2={credentials.espn_s2}; SWID={credentials.swid}"
        delay = 0.5
        for attempt in range(self._retries + 1):
            try:
                resp = await self._client.get(url, params=params, headers=headers)
            except httpx.TransportError as exc:
                if attempt == self._retries:
                    raise AdapterError(f"ESPN unreachable ({what}): {type(exc).__name__}") from exc
            else:
                if resp.status_code == 200:
                    return _json(resp, what)
                if resp.status_code in (401, 403):
                    if credentials is None:
                        raise AuthRequired(f"ESPN {what}: this league is private")
                    raise CredentialsInvalid(f"ESPN {what}: the saved cookies were refused")
                if resp.status_code == 404:
                    raise NotFoundOnPlatform(f"ESPN {what}")
                if resp.status_code not in (429, 500, 502, 503, 504) or attempt == self._retries:
                    raise AdapterError(f"ESPN {what} -> HTTP {resp.status_code}")
                delay = max(delay, _retry_after(resp))
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30.0)
        raise AssertionError("unreachable")


def _json(resp: httpx.Response, what: str) -> Any:
    try:
        return resp.json()
    except ValueError as exc:  # ESPN sometimes answers 200 with an HTML page
        raise AdapterSchemaError(f"ESPN {what} response was not JSON") from exc


def _retry_after(resp: httpx.Response) -> float:
    try:
        return min(float(resp.headers.get("Retry-After", 0)), 30.0)
    except ValueError:
        return 0.0


# --------------------------------------------------------------------------- adapter
class EspnAdapter:
    platform: Platform = "espn"

    def __init__(
        self,
        http: EspnHttp,
        season: int,
        credentials: EspnCredentials | None = None,
        *,
        base_url: str | None = None,
    ) -> None:
        self._http = http
        self._season = season
        self._credentials = credentials
        self._base = (base_url or get_settings().espn_base_url).rstrip("/")
        self._doc: _LeagueDoc | None = None  # one league read serves fetch_league + fetch_teams

    def _league_url(self, league_id: str) -> str:
        return f"{self._base}/seasons/{self._season}/segments/0/leagues/{league_id}"

    async def _league_doc(self, league_id: str) -> _LeagueDoc:
        if self._doc is not None and str(self._doc.id) == league_id:
            return self._doc
        data = await self._http.get(
            self._league_url(league_id),
            [("view", "mSettings"), ("view", "mTeam"), ("view", "mRoster")],
            self._credentials,
            what=f"league {league_id}",
        )
        doc: _LeagueDoc = _parse(_LeagueDoc, data, "league")
        self._doc = doc
        return doc

    async def probe(self, league_id: str) -> tuple[bool, str, list[tuple[str, str]]]:
        """(is_public, league name, [(team id, team name)]) from one cookie-less request.

        A private league raises AuthRequired; the connect screen then asks for the cookies.
        """
        data = await self._http.get(
            self._league_url(league_id),
            [("view", "mSettings"), ("view", "mTeam")],
            self._credentials,
            what=f"league {league_id}",
        )
        doc: _LeagueDoc = _parse(_LeagueDoc, data, "league")
        return True, doc.settings.name, [(str(t.id), _team_name(t)) for t in doc.teams]

    # -- leagues -------------------------------------------------------------
    async def find_leagues(self) -> list[tuple[LeagueRef, str | None]]:
        """Every football league the signed-in user belongs to this season, with their team id.

        Uses the fan profile espn.com's own league switcher reads. It is unofficial, so
        a shape change raises AdapterSchemaError and an anonymous profile means the cookies are
        not a real sign-in.
        """
        if self._credentials is None:
            raise AuthRequired("ESPN league list needs the user's cookies")
        fan = f"{get_settings().espn_fan_url.rstrip('/')}/{self._credentials.swid}"
        data = await self._http.get(
            fan,
            [("context", "fantasy"), ("source", "espncom-fantasy-lm")],
            self._credentials,
            what="fan profile",
        )
        doc: _FanDoc = _parse(_FanDoc, data, "fan profile")
        out: list[tuple[LeagueRef, str | None]] = []
        for pref in doc.preferences:
            entry = pref.metaData.entry if pref.metaData else None
            if entry is None or entry.gameId != FOOTBALL or entry.seasonId != self._season:
                continue
            team_id = str(entry.entryId) if entry.entryId is not None else None
            for group in entry.groups:
                ref = LeagueRef(
                    "espn", str(group.groupId), self._season, group.groupName or "ESPN league"
                )
                out.append((ref, team_id))
        return out

    async def fetch_league(self, external_id: str) -> LeagueData:
        doc = await self._league_doc(external_id)
        st = doc.settings
        if st.scoringSettings.scoringType not in (None, "H2H_POINTS"):
            raise UnsupportedLeague(
                "Sunday War Room supports head-to-head points leagues; "
                f"this league uses {st.scoringSettings.scoringType}."
            )
        return LeagueData(
            ref=LeagueRef("espn", external_id, doc.seasonId or self._season, st.name, st.size),
            avatar_url=None,
            scoring_rules=expand_espn(st.scoringSettings.scoringItems),
            roster_slots=roster_slots(st.rosterSettings.lineupSlotCounts),
            status="in_season" if doc.status.isActive else "complete",
            waivers=waiver_rules(st.acquisitionSettings),
            season_rules=season_rules(st, doc.status),
        )

    # -- teams ---------------------------------------------------------------
    async def fetch_teams(self, league: LeagueData) -> list[TeamData]:
        doc = await self._league_doc(league.ref.external_id)
        members = {m.id: m for m in doc.members}
        out = []
        for t in doc.teams:
            owner = members.get(t.primaryOwner or (t.owners[0] if t.owners else ""))
            out.append(
                TeamData(
                    external_id=str(t.id),
                    owner_external_id=t.primaryOwner or (t.owners[0] if t.owners else None),
                    name=_team_name(t),
                    owner_name=_member_name(owner),
                    avatar_url=t.logo,
                    wins=t.record.overall.wins,
                    losses=t.record.overall.losses,
                    ties=t.record.overall.ties,
                    waiver_position=t.waiverRank,
                    waiver_budget_used=t.transactionCounter.acquisitionBudgetSpent,
                    roster=build_roster(t.roster.entries if t.roster else []),
                )
            )
        return out

    # -- matchups ------------------------------------------------------------
    async def fetch_matchups(self, league: LeagueData, week: int) -> list[MatchupData]:
        """One row per team for NFL week `week` (ESPN's scoring period).

        A fantasy matchup can span two NFL weeks (some playoff rounds); `points` is then the share
        scored in `week` alone, taken from ESPN's per-period totals.
        """
        data = await self._http.get(
            self._league_url(league.ref.external_id),
            [
                ("view", "mSettings"),
                ("view", "mMatchupScore"),
                ("view", "mBoxscore"),
                ("scoringPeriodId", str(week)),
            ],
            self._credentials,
            what=f"matchups week {week}",
        )
        doc: _MatchupDoc = _parse(_MatchupDoc, data, "matchups")
        period = matchup_period_for(doc.settings.scheduleSettings, week, doc.status)
        rows: list[MatchupData] = []
        for item in doc.schedule:
            if item.matchupPeriodId != period:
                continue
            key = f"{item.matchupPeriodId}-{item.id}" if item.away is not None else None
            for side in (item.home, item.away):
                if side is None:
                    continue
                block = side.rosterForCurrentScoringPeriod or side.rosterForMatchupPeriod
                entries = block.entries if block else []
                rows.append(
                    MatchupData(
                        week=week,
                        matchup_key=key,
                        team_external_id=str(side.teamId),
                        points=side.pointsByScoringPeriod.get(str(week), side.totalPoints),
                        roster=build_roster(entries),
                        player_points={
                            str(e.playerId): e.playerPoolEntry.appliedStatTotal
                            for e in entries
                            if e.playerPoolEntry and e.playerPoolEntry.appliedStatTotal is not None
                        },
                    )
                )
        return rows

    # -- transactions --------------------------------------------------------
    async def fetch_transactions(self, league: LeagueData, week: int) -> list[TransactionData]:
        data = await self._http.get(
            self._league_url(league.ref.external_id),
            [("view", "mTransactions2"), ("scoringPeriodId", str(week))],
            self._credentials,
            what=f"transactions week {week}",
        )
        doc: _TransactionDoc = _parse(_TransactionDoc, data, "transactions")
        out = []
        for t in doc.transactions:
            kind = _TX_KINDS.get(t.type)
            adds = {str(i.playerId): str(i.toTeamId) for i in t.items if i.type == "ADD"}
            drops = {str(i.playerId): str(i.fromTeamId) for i in t.items if i.type == "DROP"}
            if kind is None or not (adds or drops):  # lineup moves and proposals aren't claims
                continue
            out.append(
                TransactionData(
                    external_id=t.id,
                    kind=kind,
                    status=_tx_status(t.status),
                    week=t.scoringPeriodId or week,
                    created_at=datetime.fromtimestamp((t.proposedDate or 0) / 1000, UTC),
                    adds=adds,
                    drops=drops,
                    waiver_bid=t.bidAmount if kind == "waiver" else None,
                )
            )
        return out


_TX_KINDS: dict[str, TransactionKind] = {
    "FREEAGENT": "free_agent",
    "WAIVER": "waiver",
    "TRADE_ACCEPT": "trade",
    "TRADE_UPHOLD": "trade",
}


def _tx_status(status: str | None) -> str:
    if status == "EXECUTED":
        return "complete"
    if (status and status.startswith("FAILED")) or status in ("CANCELED", "DECLINED", "VETOED"):
        return "failed"
    return "pending"


# --------------------------------------------------------------------------- mapping helpers
def _team_name(t: _Team) -> str:
    if t.name:
        return t.name
    joined = " ".join(x for x in (t.location, t.nickname) if x)
    return joined or t.abbrev or f"Team {t.id}"


def _member_name(m: _Member | None) -> str | None:
    if m is None:
        return None
    full = " ".join(x for x in (m.firstName, m.lastName) if x)
    return m.displayName or full or None


def roster_slots(counts: dict[str, int]) -> list[str]:
    """ESPN's `lineupSlotCounts` as an ordered list of our slots; slots we don't project are left
    out (those players show as bench)."""
    out: list[str] = []
    for slot_id in _SLOT_ORDER:
        out.extend([_SLOTS[slot_id]] * int(counts.get(str(slot_id), 0)))
    return out


def waiver_rules(a: _Acquisition) -> WaiverRules:
    """ESPN's acquisition settings in our terms; raw numbers are kept to check the mapping."""
    kind: WaiverKind
    if a.isUsingAcquisitionBudget or a.acquisitionType == "FAAB":
        kind = "faab"
    elif a.acquisitionType == "WAIVERS":
        kind = "reverse_standings" if a.waiverOrderReset else "rolling"
    else:
        kind = "none"
    raw = {
        k: int(v)
        for k, v in {
            "waiverHours": a.waiverHours,
            "waiverOrderReset": a.waiverOrderReset,
            "acquisitionBudget": a.acquisitionBudget,
            "minimumBid": a.minimumBid,
        }.items()
        if v is not None
    }
    days = [_WEEKDAYS[d] for d in a.waiverProcessDays if d in _WEEKDAYS]
    return WaiverRules(
        kind=kind,
        budget=a.acquisitionBudget if kind == "faab" else None,
        min_bid=a.minimumBid or 0,
        clear_days=math.ceil((a.waiverHours or 0) / 24),
        weekly_day=days[0] if len(days) == 1 else None,
        daily=len(days) > 1,
        raw=raw,
    )


def season_rules(st: _Settings, status: _Status) -> SeasonRules:
    sched = st.scheduleSettings
    playoff_start: int | None = None
    if sched.matchupPeriodCount:
        first_playoff_period = str(sched.matchupPeriodCount + 1)
        weeks = sched.matchupPeriods.get(first_playoff_period)
        playoff_start = weeks[0] if weeks else sched.matchupPeriodCount + 1
    round_length = sched.playoffMatchupPeriodLength or 1
    playoff_round: PlayoffRound = "two_week_rounds" if round_length >= 2 else "one_week"
    return SeasonRules(
        kind="redraft",
        start_week=status.firstScoringPeriod or 1,
        playoff_week_start=playoff_start,
        playoff_teams=sched.playoffTeamCount or None,
        playoff_round=playoff_round,
        trade_deadline=None,  # ESPN gives a date, not a week; backlog item
        trades_allowed=True,
    )


def matchup_period_for(sched: _Schedule, week: int, status: _Status) -> int:
    """The fantasy matchup period that contains NFL week `week`."""
    for period, weeks in sched.matchupPeriods.items():
        if week in weeks:
            return int(period)
    if sched.matchupPeriods:
        raise AdapterSchemaError(f"ESPN has no matchup period for NFL week {week}")
    return status.currentMatchupPeriod or week  # one matchup per week when no map is sent


def build_roster(entries: list[_Entry]) -> list[RosterSpot]:
    """Slot assignments from ESPN's roster entries. Unknown slots (IDP, punter, ...) are bench."""
    spots = []
    for e in entries:
        slot = _SLOTS.get(e.lineupSlotId, BENCH)
        player = e.playerPoolEntry.player if e.playerPoolEntry else None
        hint = None
        if player and player.fullName:
            hint = PlayerHint(
                name=player.fullName,
                position=_POSITIONS.get(player.defaultPositionId or 0),
                team=team_for_pro_team_id(player.proTeamId or 0),
            )
        spots.append(RosterSpot(str(e.playerId), slot, slot in _STARTING, hint))
    return spots


def adapter_factory(http: EspnHttp):  # type: ignore[no-untyped-def]
    """The registry hook: build one user's adapter from their EspnAccess (shares `http`)."""

    def build(access: EspnAccess) -> EspnAdapter:
        return EspnAdapter(http, access.season, access.credentials)

    return build


__all__ = [
    "EspnAccess",
    "EspnAdapter",
    "EspnCredentials",
    "EspnHttp",
    "EspnLeagueLink",
    "adapter_factory",
    "make_credentials",
    "normalize_swid",
    "parse_league_link",
]
