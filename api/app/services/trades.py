"""Trade analyzer (P2, ADR-048): lineup impact for any two teams, and trade ideas for me.

Values are this season's only (dynasty and keeper leagues are labeled so). Reads only
PostgreSQL. Trade ideas take a couple of seconds for a 12-team league, so they are computed
off the event loop and cached per league, team and sync; the "acceptable" slider then only
filters the cached list.
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import League, LeagueMembership, Player, RosterEntry, Team
from app.errors import ApiError
from app.model.lineup import LineupPlayer, optimal_lineup
from app.model.rest_of_season import Horizon
from app.model.value import (
    TradeIdea,
    TradeSide,
    ValuePlayer,
    roster_limit,
    starting_slots,
    suggest_trades,
    trade_impact,
)
from app.schemas import (
    LineupSlot,
    PlayerRef,
    RosterPlayer,
    TradeEvaluateIn,
    TradeEvaluationOut,
    TradeIdeaOut,
    TradeRostersOut,
    TradeSideOut,
    TradeSuggestionsOut,
    TradeTeam,
)
from app.services.projections import league_horizon
from app.services.views import _my_team_id, _resolve_week
from app.services.waivers import league_rosters, player_ref, value_player, weekly_points

MAX_LOSS_CAP = 3.0  # the slider's top: ideas are cached with this, then filtered
IDEAS_CACHED = 60
IDEAS_SHOWN = 15
_CACHE_SIZE = 64


@dataclass
class LeagueTrades:
    league: League
    week: int
    horizon: Horizon
    teams: dict[int, Team]
    entries: dict[int, list[RosterEntry]]  # team id -> roster this week
    players: dict[int, Player]
    points: dict[int, dict[int, float]]  # player id -> {week: points}

    @property
    def slots(self) -> list[str]:
        return starting_slots(self.league.roster_slots)

    @property
    def limit(self) -> int:
        return roster_limit(self.league.roster_slots)

    def per_week(self, total: float) -> float:
        return round(total / (self.horizon.total_weight or 1.0), 2)

    def own_per_week(self, player_id: int) -> float:
        pts = self.points.get(player_id, {})
        return self.per_week(sum(pts.get(w, 0.0) * wt for w, wt in self.horizon.weights.items()))

    def roster(self, team_id: int) -> list[ValuePlayer]:
        return [
            value_player(self.players[e.player_id], self.points.get(e.player_id, {}), e.slot)
            for e in self.entries.get(team_id, [])
            if e.player_id in self.players
        ]

    def ref(self, player_id: int) -> PlayerRef:
        return player_ref(self.players[player_id])


async def load_league_trades(db: AsyncSession, league: League) -> LeagueTrades:
    week = _resolve_week(league, None)
    horizon = league_horizon(league, week)
    points = await weekly_points(db, league, week, horizon, "ros")
    teams = {t.id: t for t in await db.scalars(select(Team).where(Team.league_id == league.id))}
    entries: dict[int, list[RosterEntry]] = {}
    for e in await league_rosters(db, league.id, week):
        entries.setdefault(e.team_id, []).append(e)
    ids = {e.player_id for es in entries.values() for e in es}
    players = {p.id: p for p in await db.scalars(select(Player).where(Player.id.in_(ids)))}
    return LeagueTrades(league, week, horizon, teams, entries, players, points)


def _season_flags(league: League, week: int) -> tuple[bool, int | None, bool]:
    rules = league.season_rules or {}
    deadline = rules.get("trade_deadline")
    return bool(rules.get("trades_allowed", True)), deadline, bool(deadline and week > deadline)


# --------------------------------------------------------------------------- rosters
async def trade_rosters_view(
    db: AsyncSession, league: League, m: LeagueMembership
) -> TradeRostersOut:
    ctx = await load_league_trades(db, league)
    order = {s: i for i, s in enumerate(dict.fromkeys(league.roster_slots))}
    teams = []
    for t in sorted(ctx.teams.values(), key=lambda t: (t.id != m.my_team_id, t.name)):
        entries = sorted(
            ctx.entries.get(t.id, []),
            key=lambda e: (order.get(e.slot, 99), -ctx.own_per_week(e.player_id)),
        )
        teams.append(
            TradeTeam(
                team_id=t.id,
                name=t.name,
                owner_name=t.owner_name,
                avatar_url=t.avatar_url,
                is_mine=t.id == m.my_team_id,
                players=[
                    RosterPlayer(
                        player=ctx.ref(e.player_id),
                        slot=e.slot,
                        points_per_week=ctx.own_per_week(e.player_id),
                    )
                    for e in entries
                    if e.player_id in ctx.players
                ],
            )
        )
    allowed, deadline, passed = _season_flags(league, ctx.week)
    return TradeRostersOut(
        league_id=league.id,
        week=ctx.week,
        horizon_weeks=list(ctx.horizon.weeks),
        league_kind=(league.season_rules or {}).get("kind", "redraft"),
        trades_allowed=allowed,
        trade_deadline=deadline,
        deadline_passed=passed,
        teams=teams,
        ready=bool(ctx.points),
    )


# --------------------------------------------------------------------------- evaluate
def _lineup(ctx: LeagueTrades, roster: Sequence[ValuePlayer]) -> list[LineupSlot]:
    """The best lineup by rest-of-season points per week (what the trade changes)."""
    players = [
        LineupPlayer(p.player_id, p.position, ctx.own_per_week(p.player_id), "BN")
        for p in roster
        if p.can_start
    ]
    result = optimal_lineup(ctx.league.roster_slots, players)
    return [
        LineupSlot(
            slot=slot,
            player=ctx.ref(pid) if pid is not None else None,
            points_per_week=ctx.own_per_week(pid) if pid is not None else 0.0,
        )
        for slot, pid in result.slots
    ]


async def evaluate_trade_view(
    db: AsyncSession, league: League, body: TradeEvaluateIn
) -> TradeEvaluationOut:
    ctx = await load_league_trades(db, league)
    a_id, b_id = body.team_a_id, body.team_b_id
    if a_id == b_id or a_id not in ctx.teams or b_id not in ctx.teams:
        raise ApiError(422, "invalid_trade", "Choose two different teams in this league")
    a_roster, b_roster = ctx.roster(a_id), ctx.roster(b_id)
    a_gives, b_gives = set(body.a_gives), set(body.b_gives)
    if not a_gives or not b_gives:
        raise ApiError(422, "invalid_trade", "Each team has to give at least one player")
    if not a_gives <= {p.player_id for p in a_roster} or not b_gives <= {
        p.player_id for p in b_roster
    }:
        raise ApiError(422, "invalid_trade", "Each player must be on the team that gives him")

    weights = ctx.horizon.weights
    a_side, b_side = await asyncio.to_thread(
        trade_impact, ctx.slots, a_roster, b_roster, a_gives, b_gives, weights, ctx.limit
    )

    def side_out(
        team_id: int,
        roster: list[ValuePlayer],
        gives: set[int],
        gets: set[int],
        incoming: list[ValuePlayer],
        s: TradeSide,
    ) -> TradeSideOut:
        after = [p for p in roster if p.player_id not in gives] + incoming
        after = [p for p in after if p.player_id not in s.dropped]
        return TradeSideOut(
            team_id=team_id,
            name=ctx.teams[team_id].name,
            gives=[ctx.ref(pid) for pid in sorted(gives)],
            gets=[ctx.ref(pid) for pid in sorted(gets)],
            before_per_week=ctx.per_week(s.before),
            after_per_week=ctx.per_week(s.after),
            change_per_week=ctx.per_week(s.change),
            dropped=[ctx.ref(pid) for pid in s.dropped],
            lineup_before=_lineup(ctx, roster),
            lineup_after=_lineup(ctx, after),
        )

    a_in = [p for p in b_roster if p.player_id in b_gives]
    b_in = [p for p in a_roster if p.player_id in a_gives]
    return TradeEvaluationOut(
        league_id=league.id,
        horizon_weeks=list(ctx.horizon.weeks),
        a=side_out(a_id, a_roster, a_gives, b_gives, a_in, a_side),
        b=side_out(b_id, b_roster, b_gives, a_gives, b_in, b_side),
    )


# --------------------------------------------------------------------------- suggestions
_ideas_cache: OrderedDict[tuple[int, int, datetime | None, int], list[TradeIdea]] = OrderedDict()


async def trade_suggestions_view(
    db: AsyncSession, league: League, m: LeagueMembership, max_loss_per_week: float
) -> TradeSuggestionsOut:
    my_id = _my_team_id(m)
    ctx = await load_league_trades(db, league)
    if not ctx.points:
        return TradeSuggestionsOut(
            league_id=league.id, max_loss_per_week=max_loss_per_week, ideas=[], ready=False
        )
    key = (league.id, my_id, league.last_synced_at, ctx.week)
    ideas = _ideas_cache.get(key)
    if ideas is None:
        others = {tid: ctx.roster(tid) for tid in ctx.teams if tid != my_id}
        ideas = await asyncio.to_thread(
            suggest_trades,
            ctx.slots,
            ctx.roster(my_id),
            others,
            ctx.horizon.weights,
            ctx.limit,
            max_loss=MAX_LOSS_CAP * ctx.horizon.total_weight,
            limit_results=IDEAS_CACHED,
        )
        _ideas_cache[key] = ideas
        while len(_ideas_cache) > _CACHE_SIZE:
            _ideas_cache.popitem(last=False)

    shown = [i for i in ideas if ctx.per_week(i.their_change) >= -max_loss_per_week][:IDEAS_SHOWN]
    return TradeSuggestionsOut(
        league_id=league.id,
        max_loss_per_week=max_loss_per_week,
        ready=True,
        ideas=[
            TradeIdeaOut(
                other_team_id=i.other_team,
                other_team_name=ctx.teams[i.other_team].name,
                gives=[ctx.ref(pid) for pid in i.gives],
                gets=[ctx.ref(pid) for pid in i.gets],
                my_change_per_week=ctx.per_week(i.my_change),
                their_change_per_week=ctx.per_week(i.their_change),
            )
            for i in shown
        ],
    )
