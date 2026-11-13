"""Game context for the projection experiments (P4): betting lines, weather, rest, team strength,
draft capital. Built once per backtest from nflverse schedules; every value a projection reads
is known before that week's kickoff (lines and conditions are pre-game; team strength uses only
earlier games).

`Extras` is passed to `project_week`; the live path passes none until an idea that needs it has
been kept and its data plumbing built.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

Key = tuple[str, int, int]  # (player, season, week)

LEAGUE_POINTS = 22.5  # a typical team score, for the first weeks of the first season
STRENGTH_PRIOR_GAMES = 4.0  # last season's scoring counts like this many games early on


@dataclass
class Extras:
    games: dict[tuple[str, int, int], dict[str, Any]]  # (team, season, week) -> pre-game facts
    strength: dict[tuple[str, int, int], float]  # (team, season, week) -> scoring vs league
    league_implied: dict[tuple[int, int], float]  # (season, week) -> mean implied score so far
    draft: dict[str, tuple[int, int]]  # gsis_id -> (draft year, round)
    cache: dict[Any, Any] = field(default_factory=dict)  # tables fitted per target season
    # (player, season, week) listed Out or Doubtful, or on a reserve list, that week (E-15)
    unavailable: set[tuple[str, int, int]] = field(default_factory=set)
    # (player, season, week) on a reserve list (injured reserve and the like) that week (E-20)
    reserve: set[tuple[str, int, int]] = field(default_factory=set)

    def game(self, team: str | None, season: int, week: int) -> dict[str, Any] | None:
        return self.games.get((str(team), season, week))


def availability(injuries: pd.DataFrame) -> tuple[set[Key], set[Key]]:
    """(unavailable, reserve) player-weeks from `load_injury_rows`: Out or Doubtful on the game
    report, or on a reserve list. Both are public before that week's kickoff."""
    if injuries.empty:
        return set(), set()
    keys = list(
        zip(
            injuries["gsis_id"].astype(str),
            injuries["season"].astype(int),
            injuries["week"].astype(int),
            strict=True,
        )
    )
    on_reserve = (injuries["roster_status"] == "RES").to_numpy()
    out = injuries["report_status"].isin(["Out", "Doubtful"]).to_numpy()
    reserve = {k for k, r in zip(keys, on_reserve, strict=True) if r}
    unavailable = reserve | {k for k, o in zip(keys, out, strict=True) if o}
    return unavailable, reserve


def build_extras(
    context: pd.DataFrame,
    draft: pd.DataFrame | None = None,
    injuries: pd.DataFrame | None = None,
) -> Extras:
    """`context`: load_game_context(...).to_pandas(); `draft`: load_draft_capital(...);
    `injuries`: load_injury_rows(...)."""
    df = context.sort_values(["team", "season", "week"]).reset_index(drop=True)

    by_team = df.groupby(["team", "season"])
    n_before = by_team.cumcount().to_numpy()
    scored_before = (by_team["points_for"].cumsum() - df["points_for"]).to_numpy()
    season_mean = by_team["points_for"].mean()
    last = np.array(
        [
            season_mean.get((t, s - 1), LEAGUE_POINTS)
            for t, s in zip(df["team"], df["season"], strict=True)
        ]
    )
    ppg = (scored_before + STRENGTH_PRIOR_GAMES * last) / (n_before + STRENGTH_PRIOR_GAMES)
    df["ppg"] = ppg
    league_ppg = df.groupby(["season", "week"])["ppg"].transform("mean")
    df["strength"] = df["ppg"] / league_ppg

    weekly = df.groupby(["season", "week"])["implied"].agg(["sum", "count"]).sort_index()
    cum_sum = weekly["sum"].cumsum().shift(1)
    cum_n = weekly["count"].cumsum().shift(1)
    league_implied = (cum_sum / cum_n).fillna(LEAGUE_POINTS)

    games = {
        (str(r["team"]), int(r["season"]), int(r["week"])): {str(k): v for k, v in r.items()}
        for r in df.drop(columns=["ppg", "strength"]).to_dict("records")
    }
    strength = {
        (str(t), int(s), int(w)): float(v)
        for t, s, w, v in zip(df["team"], df["season"], df["week"], df["strength"], strict=True)
    }
    drafted: dict[str, tuple[int, int]] = {}
    if draft is not None and not draft.empty:
        drafted = {
            str(g): (int(y), int(r))
            for g, y, r in zip(draft["gsis_id"], draft["draft_year"], draft["round"], strict=True)
        }
    weeks: list[Any] = league_implied.index.tolist()
    unavailable, reserve = availability(injuries) if injuries is not None else (set(), set())
    return Extras(
        games,
        strength,
        {(int(s), int(w)): float(v) for (s, w), v in zip(weeks, league_implied, strict=True)},
        drafted,
        unavailable=unavailable,
        reserve=reserve,
    )


def is_dome(roof: Any) -> bool:
    return str(roof).lower() in {"dome", "closed"}
