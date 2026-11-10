"""Roster value: what a set of players is worth to a team over a set of weeks (P2). Pure.

Shared by waivers (ADR-047: value added to *my* best lineup) and trades (ADR-048: lineup
impact for both teams). A team's value is, for every week in the horizon, the points of its
best possible starting lineup that week, times the week's weight, summed. So byes, injuries
and the league's slots all count, and a bench player only adds value in weeks he would start.

Roster spots count: a team over its roster limit drops whoever costs it the least.

The best lineup is found with the matroid greedy algorithm: take players from most to least
projected points, keep each one if the kept set can still be matched to distinct eligible
slots (checked with an augmenting path). Exact for any slot mix, and much faster than the
Hungarian method in lineup.py, which waivers and trades would call thousands of times.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from itertools import combinations

from app.model.lineup import ELIGIBLE

NOT_ON_ROSTER_LIMIT = frozenset({"IR", "TAXI"})  # slots that don't count toward roster size


@dataclass(frozen=True)
class ValuePlayer:
    player_id: int
    position: str
    weekly: Mapping[int, float]  # week -> projected points
    can_start: bool = True  # False for taxi-squad players
    counts_toward_limit: bool = True  # False for players in IR / taxi slots


def starting_slots(roster_slots: Sequence[str]) -> list[str]:
    return [s for s in roster_slots if s in ELIGIBLE]


def roster_limit(roster_slots: Sequence[str]) -> int:
    """How many players a team may carry outside IR / taxi (starters + bench)."""
    return sum(1 for s in roster_slots if s not in NOT_ON_ROSTER_LIMIT)


@lru_cache(maxsize=64)
def _slot_index(slots: tuple[str, ...]) -> dict[str, tuple[int, ...]]:
    """position -> the starting slots (by index) it may fill."""
    positions = {p for s in slots for p in ELIGIBLE[s]}
    return {p: tuple(i for i, s in enumerate(slots) if p in ELIGIBLE[s]) for p in positions}


def best_lineup(
    slots: Sequence[str], players: Sequence[tuple[str, float]]
) -> tuple[float, set[int]]:
    """(points, indices of the players used) of the best lineup for these starting slots."""
    fits = _slot_index(tuple(slots))
    owner: list[int | None] = [None] * len(slots)  # slot -> index into `players`
    open_slots = len(slots)
    used: set[int] = set()
    total = 0.0
    for i in sorted(range(len(players)), key=lambda i: -players[i][1]):
        pos, pts = players[i]
        if pts <= 0 or open_slots == 0:
            break
        if pos in fits and _augment(i, players, fits, owner, set()):
            total += pts
            used.add(i)
            open_slots -= 1
    return total, used


def best_lineup_points(slots: Sequence[str], players: Iterable[tuple[str, float]]) -> float:
    """Points of the best lineup from (position, points) pairs for these starting slots."""
    return best_lineup(slots, list(players))[0]


def _augment(
    player: int,
    players: Sequence[tuple[str, float]],
    fits: Mapping[str, tuple[int, ...]],
    owner: list[int | None],
    seen: set[int],
) -> bool:
    """Kuhn's augmenting path: give `player` a slot, moving earlier picks if needed."""
    for i in fits[players[player][0]]:
        if i in seen:
            continue
        seen.add(i)
        holder = owner[i]
        if holder is None or _augment(holder, players, fits, owner, seen):
            owner[i] = player
            return True
    return False


def team_value(
    slots: Sequence[str], players: Iterable[ValuePlayer], weights: Mapping[int, float]
) -> float:
    """Weighted sum over the horizon of the best lineup's points each week."""
    starters = [p for p in players if p.can_start]
    return sum(
        weight
        * best_lineup_points(slots, ((p.position, p.weekly.get(week, 0.0)) for p in starters))
        for week, weight in weights.items()
    )


def never_starting(
    slots: Sequence[str], players: Sequence[ValuePlayer], weights: Mapping[int, float]
) -> list[ValuePlayer]:
    """Players who make the best lineup in no week of the horizon (losing them costs 0)."""
    used: set[int] = set()
    for week in weights:
        _, idx = best_lineup(
            slots, [(p.position, p.weekly.get(week, 0.0) if p.can_start else 0.0) for p in players]
        )
        used |= idx
    return [p for i, p in enumerate(players) if i not in used]


def fit_to_limit(
    slots: Sequence[str], players: Sequence[ValuePlayer], limit: int, weights: Mapping[int, float]
) -> tuple[list[ValuePlayer], list[ValuePlayer]]:
    """Drop the cheapest players (by lost value) until the roster fits. Returns (kept, dropped).

    Players who never make the best lineup cost nothing, so the lowest-projected of them goes
    first; only when every player starts somewhere is each drop's cost measured.
    """
    kept = list(players)
    dropped: list[ValuePlayer] = []
    while sum(p.counts_toward_limit for p in kept) > limit:
        free = [p for p in never_starting(slots, kept, weights) if p.counts_toward_limit]
        candidates = free or [p for p in kept if p.counts_toward_limit]
        # The cheapest player to lose is the one whose absence leaves the most value; between
        # equally unneeded players (bench depth), the one projected for fewer points.
        cheapest = max(
            candidates,
            key=lambda d: (
                0.0 if free else team_value(slots, [p for p in kept if p is not d], weights),
                -sum(d.weekly.values()),
                -d.player_id,
            ),
        )
        kept.remove(cheapest)
        dropped.append(cheapest)
    return kept, dropped


# --------------------------------------------------------------------------- waivers
@dataclass(frozen=True)
class AddResult:
    player_id: int
    gain: float  # weighted points the best lineup gains, after any drop
    drop_id: int | None  # who to drop to make room (None if there's an open spot)


def waiver_gains(
    slots: Sequence[str],
    roster: Sequence[ValuePlayer],
    candidates: Sequence[ValuePlayer],
    weights: Mapping[int, float],
    limit: int,
    *,
    drop_choices: int = 3,
) -> list[AddResult]:
    """Value added by each candidate to this roster, best first (ADR-047)."""
    base = team_value(slots, roster, weights)
    full = sum(p.counts_toward_limit for p in roster) >= limit
    # The cheapest players to lose, measured once on the current roster.
    drops = sorted(
        (p for p in roster if p.counts_toward_limit),
        key=lambda d: (base - team_value(slots, [p for p in roster if p is not d], weights),
                       d.player_id),
    )[:drop_choices] if full else []  # fmt: skip
    # Each week, the weakest starter: a candidate scoring below it can't improve the lineup.
    floor = {
        w: _weakest_starter(
            slots, [(p.position, p.weekly.get(w, 0.0)) for p in roster if p.can_start]
        )
        for w in weights
    }

    results = []
    for c in candidates:
        if not any(c.weekly.get(w, 0.0) > floor[w] for w in weights):
            results.append(AddResult(c.player_id, 0.0, None))
            continue
        if not full:
            gain = team_value(slots, [*roster, c], weights) - base
            results.append(AddResult(c.player_id, round(gain, 2), None))
            continue
        best = max(
            ((team_value(slots, [*(p for p in roster if p is not d), c], weights) - base, d)
             for d in drops),
            key=lambda t: (t[0], -t[1].player_id),
        )  # fmt: skip
        results.append(AddResult(c.player_id, round(best[0], 2), best[1].player_id))
    return sorted(results, key=lambda r: (-r.gain, r.player_id))


def _weakest_starter(slots: Sequence[str], players: Sequence[tuple[str, float]]) -> float:
    """Points of the lowest player in the best lineup (0 if a slot would stay empty)."""
    _, used = best_lineup(slots, players)
    if len(used) < len(slots):
        return 0.0
    return min(players[i][1] for i in used)


# --------------------------------------------------------------------------- trades
@dataclass(frozen=True)
class TradeSide:
    before: float
    after: float
    dropped: list[int] = field(default_factory=list)

    @property
    def change(self) -> float:
        return round(self.after - self.before, 2)


def trade_impact(
    slots: Sequence[str],
    team_a: Sequence[ValuePlayer],
    team_b: Sequence[ValuePlayer],
    a_gives: set[int],
    b_gives: set[int],
    weights: Mapping[int, float],
    limit: int,
    *,
    before: tuple[float, float] | None = None,
) -> tuple[TradeSide, TradeSide]:
    """Each team's best-lineup value before and after the trade (ADR-048: lineup impact).

    `before`: both teams' current values, when the caller already has them.
    """

    def side(
        mine: Sequence[ValuePlayer],
        gives: set[int],
        gets: Sequence[ValuePlayer],
        value_now: float | None,
    ) -> TradeSide:
        now = team_value(slots, mine, weights) if value_now is None else value_now
        incoming = [ValuePlayer(p.player_id, p.position, p.weekly) for p in gets]  # active spot
        after_roster = [p for p in mine if p.player_id not in gives] + incoming
        kept, dropped = fit_to_limit(slots, after_roster, limit, weights)
        return TradeSide(round(now, 2), round(team_value(slots, kept, weights), 2),
                         [p.player_id for p in dropped])  # fmt: skip

    a_gets = [p for p in team_b if p.player_id in b_gives]
    b_gets = [p for p in team_a if p.player_id in a_gives]
    a_now, b_now = before if before else (None, None)
    return side(team_a, a_gives, a_gets, a_now), side(team_b, b_gives, b_gets, b_now)


@dataclass(frozen=True)
class TradeIdea:
    other_team: int
    gives: tuple[int, ...]  # my players
    gets: tuple[int, ...]  # their players
    my_change: float
    their_change: float


def suggest_trades(
    slots: Sequence[str],
    mine: Sequence[ValuePlayer],
    others: Mapping[int, Sequence[ValuePlayer]],
    weights: Mapping[int, float],
    limit: int,
    *,
    max_loss: float,
    shortlist: int = 6,
    limit_results: int = 10,
) -> list[TradeIdea]:
    """Best trades for me that the other team loses at most `max_loss` on (ADR-048).

    Searches 1-for-1, 2-for-1 and 1-for-2 deals. To stay fast it only considers, per team,
    the `shortlist` pieces on each side that look best: their players that would help my
    lineup more than they cost theirs, and my players that would help theirs more than they
    cost mine (surplus depth). `max_loss` is in the same weighted points as the values.
    """
    base_me = team_value(slots, mine, weights)

    def helps(roster: Sequence[ValuePlayer], base: float, p: ValuePlayer) -> float:
        newcomer = ValuePlayer(p.player_id, p.position, p.weekly)
        return team_value(slots, [*roster, newcomer], weights) - base

    def costs(roster: Sequence[ValuePlayer], base: float, p: ValuePlayer) -> float:
        return base - team_value(slots, [q for q in roster if q is not p], weights)

    tradeable_mine = [p for p in mine if p.can_start]
    ideas: list[TradeIdea] = []
    for team_id, theirs in others.items():
        base_them = team_value(slots, theirs, weights)
        want = sorted(
            (p for p in theirs if p.can_start),
            key=lambda p: costs(theirs, base_them, p) - helps(mine, base_me, p),
        )[:shortlist]
        offer = sorted(
            tradeable_mine,
            key=lambda p: costs(mine, base_me, p) - helps(theirs, base_them, p),
        )[:shortlist]
        Deal = tuple[tuple[ValuePlayer, ...], tuple[ValuePlayer, ...]]
        deals: list[Deal] = [((g,), (t,)) for g in offer for t in want]
        deals += [(g2, (t,)) for g2 in combinations(offer[:4], 2) for t in want[:3]]
        deals += [((g,), t2) for g in offer[:3] for t2 in combinations(want[:4], 2)]
        for gives, gets in deals:
            give_ids = tuple(p.player_id for p in gives)
            get_ids = tuple(p.player_id for p in gets)
            me, them = trade_impact(
                slots, mine, theirs, set(give_ids), set(get_ids), weights, limit,
                before=(base_me, base_them),
            )  # fmt: skip
            if me.change > 0 and them.change >= -max_loss:
                ideas.append(TradeIdea(team_id, give_ids, get_ids, me.change, them.change))
    ideas.sort(key=lambda i: (-i.my_change, -i.their_change, i.other_team, i.gives, i.gets))
    return ideas[:limit_results]
