"""Win probability by simulation (Projection Model: Lineup and matchup). Pure.

Each starter's score is drawn from their projected range (distribution.sample); both lineups
are summed per draw; win chance = share of draws where my total is higher (ties count half).
v1 draws players independently; correlations (a QB and his own receivers) are a later upgrade.

Points already scored are fixed: for a player whose game is over, pass p10 = p50 = p90 = actual.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from app.model.distribution import sample

DRAWS = 10_000


@dataclass(frozen=True)
class SimPlayer:
    p10: float
    p50: float
    p90: float
    floor: float = 0.0


@dataclass(frozen=True)
class SimResult:
    win_prob: float
    my_median: float
    opp_median: float
    my_p10: float
    my_p90: float
    opp_p10: float
    opp_p90: float


def _totals(team: Sequence[SimPlayer], rng: np.random.Generator, draws: int) -> np.ndarray:
    if not team:
        return np.zeros(draws)
    arr = np.array([(p.p10, p.p50, p.p90, p.floor) for p in team], dtype=float)
    out: np.ndarray = sample(arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3], draws, rng).sum(axis=1)
    return out


def simulate(
    mine: Sequence[SimPlayer], theirs: Sequence[SimPlayer], *, draws: int = DRAWS, seed: int = 7
) -> SimResult:
    """Seeded, so the same inputs always give the same answer (no flicker between refreshes)."""
    rng = np.random.default_rng(seed)
    a, b = _totals(mine, rng, draws), _totals(theirs, rng, draws)
    win = float(np.mean(a > b) + 0.5 * np.mean(a == b))

    def q(x: np.ndarray, p: float) -> float:
        return round(float(np.quantile(x, p)), 1)

    return SimResult(
        round(win, 4), q(a, 0.5), q(b, 0.5), q(a, 0.1), q(a, 0.9), q(b, 0.1), q(b, 0.9)
    )
