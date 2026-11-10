"""Rest-of-season projections (P2, ADR-047/048). Pure: DataFrames in, DataFrame out.

Simple on purpose (ADR-043: smarter long-range projections are P5). For each remaining week
of the league's fantasy season, the weekly model (`project_week`) is run with:

* what is known **now**: only games before the first remaining week count (no leakage), so a
  player's baseline is the same every week;
* that week's real opponent from the NFL schedule (byes give 0);
* injuries applied only as long as they plausibly last: Out / Doubtful / Questionable affect
  the next game only; IR / PUP / suspended / NFI affect the next IR_WEEKS weeks.

The total weights fantasy playoff weeks by PLAYOFF_WEIGHT (owner decision, 2026-11-09) and
does not fade far-off weeks. Bump MODEL_VERSION in projection.py with any change to the math.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.adapters.base import PlayoffRound
from app.model.projection import Context, project_week

PLAYOFF_WEIGHT = 1.5
IR_WEEKS = 4  # the shortest typical stay on injured reserve
LAST_NFL_WEEK = 18
DEFAULT_LAST_FANTASY_WEEK = 17  # when a league has no playoffs set
SHORT_TERM = frozenset({"out", "doubtful", "questionable"})
LONG_TERM = frozenset({"ir", "pup", "sus", "na", "nfi"})
UNKNOWN_OPPONENT = "TBD"  # schedule not loaded for that week: no opponent adjustment


@dataclass(frozen=True)
class Horizon:
    weeks: tuple[int, ...]
    weights: dict[int, float]
    playoff_weeks: frozenset[int]

    @property
    def total_weight(self) -> float:
        return sum(self.weights.values())


def last_fantasy_week(
    playoff_week_start: int | None,
    playoff_teams: int | None,
    playoff_round: PlayoffRound = "one_week",
) -> int:
    """The league's final scoring week, from its playoff settings."""
    if not playoff_week_start or not playoff_teams or playoff_teams < 2:
        return DEFAULT_LAST_FANTASY_WEEK
    rounds = math.ceil(math.log2(playoff_teams))
    length = {"one_week": rounds, "two_week_final": rounds + 1, "two_week_rounds": rounds * 2}
    return min(playoff_week_start + length[playoff_round] - 1, LAST_NFL_WEEK)


def season_horizon(
    from_week: int,
    playoff_week_start: int | None,
    playoff_teams: int | None,
    playoff_round: PlayoffRound = "one_week",
) -> Horizon:
    """Remaining weeks (from_week through the last fantasy week) and how much each counts."""
    last = last_fantasy_week(playoff_week_start, playoff_teams, playoff_round)
    weeks = tuple(range(from_week, last + 1))
    playoffs = frozenset(w for w in weeks if playoff_week_start and w >= playoff_week_start)
    weights = {w: PLAYOFF_WEIGHT if w in playoffs else 1.0 for w in weeks}
    return Horizon(weeks, weights, playoffs)


def single_week(week: int) -> Horizon:
    return Horizon((week,), {week: 1.0}, frozenset())


def _injury_for(status: Any, index: int) -> str | None:
    """The injury status the model should see `index` weeks from now."""
    s = str(status or "").strip()
    low = s.lower()
    if low in SHORT_TERM:
        return s if index == 0 else None
    if low in LONG_TERM:
        return s if index < IR_WEEKS else None
    return s or None


def project_rest_of_season(
    history: pd.DataFrame,
    targets: pd.DataFrame,
    season: int,
    horizon: Horizon,
    schedule: dict[int, dict[str, str]],
) -> pd.DataFrame:
    """Project every target across the horizon.

    targets: like `project_week`'s, without `opponent` (taken from `schedule`).
    schedule: week -> {team: opponent}; a week with no games loaded gets UNKNOWN_OPPONENT,
              a team missing from a loaded week is on bye.
    Returns targets + `ros_points` (weighted total), `games` (weeks with a game) and `weekly`
    ([{week, points, weight, opponent}]).
    """
    if targets.empty or not horizon.weeks:
        empty = targets.copy()
        empty["ros_points"] = 0.0
        empty["games"] = 0
        no_weeks: list[list[Any]] = [[] for _ in range(len(empty))]
        empty["weekly"] = pd.Series(no_weeks, index=empty.index, dtype=object)
        return empty

    ctx = Context(season, horizon.weeks[0])
    per_week: list[pd.DataFrame] = []
    for i, week in enumerate(horizon.weeks):
        games = schedule.get(week)
        t = targets.copy()
        if games:
            t["opponent"] = [games.get(team) for team in t["team"]]
        else:
            t["opponent"] = UNKNOWN_OPPONENT
        if "injury_status" in t:
            t["injury_status"] = [_injury_for(s, i) for s in t["injury_status"]]
        projected = project_week(history, t, ctx, calibration=None)
        per_week.append(
            pd.DataFrame(
                {
                    "row": range(len(t)),
                    "week": week,
                    "points": projected["points"].to_numpy(),
                    "opponent": t["opponent"].to_numpy(),
                }
            )
        )

    long = pd.concat(per_week, ignore_index=True)
    long["weight"] = long["week"].map(horizon.weights)
    out = targets.reset_index(drop=True).copy()
    totals = (long["points"] * long["weight"]).groupby(long["row"]).sum()
    out["ros_points"] = totals.reindex(range(len(out)), fill_value=0.0).round(2).to_numpy()
    played = long[long["opponent"].notna()].groupby("row").size()
    out["games"] = played.reindex(range(len(out)), fill_value=0).astype(int).to_numpy()
    weekly: list[list[dict[str, Any]]] = [[] for _ in range(len(out))]
    for r in long.to_dict("records"):
        weekly[int(r["row"])].append(
            {
                "week": int(r["week"]),
                "points": round(float(r["points"]), 2),
                "weight": float(r["weight"]),
                "opponent": None if pd.isna(r["opponent"]) else str(r["opponent"]),
            }
        )
    out["weekly"] = pd.Series(weekly, index=out.index, dtype=object)
    return out
