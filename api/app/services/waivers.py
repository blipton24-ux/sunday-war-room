"""Waivers screen (P2, ADR-047): free agents ranked by value added to my best lineup.

Reads only PostgreSQL: rosters from the last sync, rest-of-season and weekly projections from
the worker, recent drops from the league's transactions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    League,
    LeagueMembership,
    LeagueTransaction,
    Player,
    Projection,
    RestOfSeasonProjection,
    RosterEntry,
    Team,
)
from app.model.lineup import ELIGIBLE
from app.model.projection import MODEL_VERSION
from app.model.rest_of_season import Horizon, single_week
from app.model.scoring import scoring_key
from app.model.value import ValuePlayer, roster_limit, starting_slots, waiver_gains
from app.model.waivers import faab_bid, waiver_status
from app.schemas import PlayerRef, WaiverPlayer, WaiversOut
from app.services.projections import ROS_MODEL_VERSION, horizon_key, league_horizon
from app.services.views import _my_team_id, _resolve_week, headshot

WaiverHorizon = Literal["ros", "week"]
MAX_RESULTS = 40


def player_ref(p: Player) -> PlayerRef:
    return PlayerRef(
        player_id=p.id,
        name=p.name,
        position=p.position,
        nfl_team=p.nfl_team,
        headshot_url=headshot(p),
        injury_status=p.injury_status,
    )


async def league_rosters(db: AsyncSession, league_id: int, week: int) -> list[RosterEntry]:
    return list(
        await db.scalars(
            select(RosterEntry)
            .join(Team, Team.id == RosterEntry.team_id)
            .where(Team.league_id == league_id, RosterEntry.week == week)
        )
    )


async def weekly_points(
    db: AsyncSession, league: League, week: int, horizon: Horizon, which: WaiverHorizon
) -> dict[int, dict[int, float]]:
    """player_id -> {week: projected points} for every projected player in the horizon."""
    key = league.scoring_key or scoring_key(league.scoring_rules)
    if which == "week":
        rows = await db.execute(
            select(Projection.player_id, Projection.points).where(
                Projection.season == league.season,
                Projection.week == week,
                Projection.scoring_key == key,
                Projection.model_version == MODEL_VERSION,
            )
        )
        return {pid: {week: pts} for pid, pts in rows}
    ros = await db.execute(
        select(RestOfSeasonProjection.player_id, RestOfSeasonProjection.weekly).where(
            RestOfSeasonProjection.season == league.season,
            RestOfSeasonProjection.from_week == week,
            RestOfSeasonProjection.scoring_key == key,
            RestOfSeasonProjection.horizon_key == horizon_key(horizon),
            RestOfSeasonProjection.model_version == ROS_MODEL_VERSION,
        )
    )
    return {pid: {int(w["week"]): float(w["points"]) for w in weekly} for pid, weekly in ros}


def value_player(p: Player, points: dict[int, float], slot: str = "BN") -> ValuePlayer:
    return ValuePlayer(
        p.id,
        p.position or "",
        points,
        can_start=slot != "TAXI",
        counts_toward_limit=slot not in ("IR", "TAXI"),
    )


async def last_drops(db: AsyncSession, league_id: int) -> dict[str, datetime]:
    """Platform player id -> when he was last dropped (completed transactions only)."""
    rows = await db.scalars(
        select(LeagueTransaction)
        .where(LeagueTransaction.league_id == league_id, LeagueTransaction.status == "complete")
        .order_by(LeagueTransaction.created_at)
    )
    out: dict[str, datetime] = {}
    for t in rows:
        for pid in t.drops or {}:
            out[pid] = t.created_at
        for pid in t.adds or {}:
            out.pop(pid, None)  # picked up again: no longer on waivers
    return out


async def waivers_view(
    db: AsyncSession,
    league: League,
    m: LeagueMembership,
    which: WaiverHorizon,
    *,
    now: datetime | None = None,
) -> WaiversOut:
    now = now or datetime.now(UTC)
    week = _resolve_week(league, None)
    my_id = _my_team_id(m)
    me = await db.get(Team, my_id)
    assert me is not None

    horizon = league_horizon(league, week) if which == "ros" else single_week(week)
    weights = horizon.weights
    points = await weekly_points(db, league, week, horizon, which)

    entries = await league_rosters(db, league.id, week)
    rostered = {e.player_id for e in entries}
    mine = [e for e in entries if e.team_id == my_id]
    usable = {pos for slot in starting_slots(league.roster_slots) for pos in ELIGIBLE[slot]}
    wanted = {e.player_id for e in mine} | {pid for pid in points if pid not in rostered}
    players = {p.id: p for p in await db.scalars(select(Player).where(Player.id.in_(wanted)))}

    roster = [value_player(players[e.player_id], points.get(e.player_id, {}), e.slot)
              for e in mine if e.player_id in players]  # fmt: skip
    candidates = [
        value_player(p, points[p.id])
        for p in players.values()
        if p.id not in rostered and p.position in usable and p.id in points
    ]
    slots = starting_slots(league.roster_slots)
    gains = waiver_gains(slots, roster, candidates, weights, roster_limit(league.roster_slots))

    rules = league.waiver_rules or {}
    kind = rules.get("kind", "none")
    budget = rules.get("budget") if kind == "faab" else None
    remaining = None if budget is None else max(0, budget - (me.waiver_budget_used or 0))
    drops = await last_drops(db, league.id)
    total_weight = horizon.total_weight or 1.0

    out: list[WaiverPlayer] = []
    for g in gains[:MAX_RESULTS]:
        p = players[g.player_id]
        status, until = waiver_status(drops.get(p.sleeper_id or ""), rules, now)
        per_week = g.gain / total_weight
        bid = faab_bid(per_week, remaining, int(rules.get("min_bid") or 0)) if remaining else None
        own = sum(points[p.id].get(w, 0.0) * wt for w, wt in weights.items()) / total_weight
        out.append(
            WaiverPlayer(
                player=player_ref(p),
                gain=g.gain,
                gain_per_week=round(per_week, 2),
                points_per_week=round(own, 2),
                status=status,
                on_waivers_until=until,
                drop=player_ref(players[g.drop_id]) if g.drop_id else None,
                bid_low=bid[0] if bid else None,
                bid_high=bid[1] if bid else None,
            )
        )

    return WaiversOut(
        league_id=league.id,
        week=week,
        horizon=which,
        horizon_weeks=list(horizon.weeks),
        playoff_weeks=sorted(horizon.playoff_weeks),
        waiver_kind=kind,
        faab_budget=budget,
        faab_remaining=remaining,
        my_waiver_position=me.waiver_position if kind in ("rolling", "reverse_standings") else None,
        clear_days=int(rules.get("clear_days") or 0),
        players=out,
        ready=bool(candidates),
    )
