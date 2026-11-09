"""Optimal lineup + swap suggestions (Projection Model: Lineup and matchup). Pure.

Fills the league's starting slots to maximize projected points, respecting eligibility.
Players whose game has started are *locked*: they stay where they are and can't be moved in
or out (you can't change them in Sleeper either).

Method: an exact assignment (Hungarian algorithm) of players to open slots, maximizing total
projected points. Exact for any slot mix, including overlapping flex types such as
REC_FLEX + WRRB_FLEX where "fill restrictive slots first" can be wrong.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

ELIGIBLE: dict[str, frozenset[str]] = {
    "QB": frozenset({"QB"}),
    "RB": frozenset({"RB"}),
    "WR": frozenset({"WR"}),
    "TE": frozenset({"TE"}),
    "K": frozenset({"K"}),
    "DEF": frozenset({"DEF"}),
    "REC_FLEX": frozenset({"WR", "TE"}),
    "WRRB_FLEX": frozenset({"WR", "RB"}),
    "FLEX": frozenset({"RB", "WR", "TE"}),
    "SUPER_FLEX": frozenset({"QB", "RB", "WR", "TE"}),
}


@dataclass(frozen=True)
class LineupPlayer:
    player_id: int
    position: str
    points: float
    current_slot: str  # a starting slot, or BN / IR / TAXI
    locked: bool = False


@dataclass(frozen=True)
class Swap:
    slot: str
    player_in: int
    player_out: int | None  # None: the slot was empty
    gain: float


@dataclass
class LineupResult:
    slots: list[tuple[str, int | None]]  # optimal: (slot, player_id) in league slot order
    current_points: float
    optimal_points: float
    swaps: list[Swap] = field(default_factory=list)


def _eligible(slot: str, p: LineupPlayer) -> bool:
    return p.position in ELIGIBLE.get(slot, frozenset())


def _hungarian_max(weights: np.ndarray) -> list[int]:
    """Assignment maximizing total weight (rows -> distinct columns); needs rows <= cols.

    Classic O(n^3) Kuhn-Munkres with potentials, run on costs = -weights.
    Returns, for each row, the column it gets.
    """
    n_rows, n_cols = weights.shape
    cost = -weights
    u = np.zeros(n_rows + 1)
    v = np.zeros(n_cols + 1)
    match = np.zeros(n_cols + 1, dtype=int)  # match[col] = row (1-based), 0 = free
    way = np.zeros(n_cols + 1, dtype=int)
    for row in range(1, n_rows + 1):
        match[0] = row
        col0 = 0
        minv = np.full(n_cols + 1, np.inf)
        used = np.zeros(n_cols + 1, dtype=bool)
        while True:
            used[col0] = True
            r0 = match[col0]
            delta, col1 = np.inf, 0
            for c in range(1, n_cols + 1):
                if not used[c]:
                    cur = cost[r0 - 1, c - 1] - u[r0] - v[c]
                    if cur < minv[c]:
                        minv[c], way[c] = cur, col0
                    if minv[c] < delta:
                        delta, col1 = minv[c], c
            for c in range(n_cols + 1):
                if used[c]:
                    u[match[c]] += delta
                    v[c] -= delta
                else:
                    minv[c] -= delta
            col0 = col1
            if match[col0] == 0:
                break
        while col0:
            col1 = way[col0]
            match[col0] = match[col1]
            col0 = col1
    result = [0] * n_rows
    for c in range(1, n_cols + 1):
        if match[c]:
            result[match[c] - 1] = c - 1
    return result


INELIGIBLE = -1e6  # an ineligible pairing; never chosen while any eligible option exists


def optimal_lineup(roster_slots: Sequence[str], players: Sequence[LineupPlayer]) -> LineupResult:
    starting = [s for s in roster_slots if s in ELIGIBLE]
    by_id = {p.player_id: p for p in players}
    assigned: list[int | None] = [None] * len(starting)

    # Locked starters keep their slot (one per slot, in order).
    for i, slot in enumerate(starting):
        for p in players:
            if p.locked and p.current_slot == slot and p.player_id not in assigned:
                assigned[i] = p.player_id
                break

    open_slots = [i for i, pid in enumerate(assigned) if pid is None]
    pool = [p for p in players if not p.locked and p.current_slot not in ("IR", "TAXI")]
    if open_slots and pool:
        # Columns: real players, then one "leave empty" column per open slot (weight 0).
        w = np.full((len(open_slots), len(pool) + len(open_slots)), INELIGIBLE)
        w[:, len(pool) :] = 0.0
        for r, i in enumerate(open_slots):
            for c, p in enumerate(pool):
                if _eligible(starting[i], p):
                    # A tiny tie-break keeps the current starter when projections are equal.
                    w[r, c] = p.points + (1e-6 if p.current_slot == starting[i] else 0.0)
        for r, c in enumerate(_hungarian_max(w)):
            if c < len(pool) and w[r, c] > INELIGIBLE / 2:
                assigned[open_slots[r]] = pool[c].player_id

    slots = list(zip(starting, assigned, strict=True))
    current_points = sum(p.points for p in players if p.current_slot in ELIGIBLE)
    optimal_points = sum(by_id[pid].points for pid in assigned if pid is not None)
    return LineupResult(
        slots=slots,
        current_points=round(current_points, 2),
        optimal_points=round(optimal_points, 2),
        swaps=suggest_swaps(starting, assigned, players),
    )


def suggest_swaps(
    starting: Sequence[str], optimal: Sequence[int | None], players: Sequence[LineupPlayer]
) -> list[Swap]:
    """Pair each player entering the lineup with the specific starter whose place they take.

    Incoming players (in the optimal lineup, not starting now) are matched to outgoing players
    (starting now, not in the optimal lineup). Each incoming player replaces the lowest-projected
    outgoing player they're eligible to replace, so every swap is a move the user can make.
    """
    by_id = {p.player_id: p for p in players}
    current_starters = {p.player_id for p in players if p.current_slot in ELIGIBLE}
    optimal_set = {pid for pid in optimal if pid is not None}
    incoming = sorted(
        (by_id[pid] for pid in optimal_set - current_starters), key=lambda p: -p.points
    )
    outgoing = sorted(
        (by_id[pid] for pid in current_starters - optimal_set), key=lambda p: p.points
    )
    empty_slots = [
        s for s in starting
        if sum(1 for p in players if p.current_slot == s) < list(starting).count(s)
    ]  # fmt: skip

    swaps = []
    for p_in in incoming:
        match = next((o for o in outgoing if _eligible(o.current_slot, p_in)), None)
        if match is None:
            match = next(iter(outgoing), None)
        if match is not None:
            outgoing.remove(match)
            swaps.append(Swap(match.current_slot, p_in.player_id, match.player_id,
                              round(p_in.points - match.points, 2)))  # fmt: skip
        else:
            slot = next((s for s in empty_slots if _eligible(s, p_in)), "FLEX")
            if slot in empty_slots:
                empty_slots.remove(slot)
            swaps.append(Swap(slot, p_in.player_id, None, round(p_in.points, 2)))
    return swaps
