"""Mark player-games spoiled by an injury (ADR-054).

A player hurt before or during a game scores for a reason no model could know, so backtests
leave those games out of the headline numbers. The rule is fixed here, was checked by hand
against known games before any experiment used it, and is never tuned against model results.

Labels (`None` means a normal game):
  "before"        listed Out or Doubtful that week and played anyway (a late change)
  "during"        his snap share collapsed against his own recent normal AND there is direct
                  evidence of an injury at his team's next game: an injury-report designation
                  (Out, Doubtful, Questionable) or a reserve-list listing (injured reserve)
  "questionable"  listed Questionable and played: kept, but counted on its own line

Why evidence and not "he missed his next game": a hand check found that rule also flags a
backup quarterback replaced by the returning starter. Roster status separates the two (the
injured show as reserve, the benched stay active). Both pieces of evidence are public before the
next kickoff, so the same marking is used to judge games and to leave them out of a player's own
history without looking at anything that happened later. (For a bye week the evidence comes from
the team's next game week, a week later than the week being projected; that only matters for a
projection of 0 anyway.)

The cost of being strict: an injury with no report line and no reserve listing (a player who
misses a game and is simply not on the report) is not marked. Kickers and defenses carry no snap
share, so they never get "during".
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

OUT_STATUSES = frozenset({"Out", "Doubtful"})
REPORT_STATUSES = frozenset({"Out", "Doubtful", "Questionable"})
RESERVE = "RES"
SNAP_DROP = 0.5  # snap share under half his own recent normal
RECENT_GAMES = 4  # his recent normal: the mean of up to this many earlier games
MIN_RECENT_GAMES = 2
MIN_NORMAL_SNAP = 0.30  # only players who normally play count (a backup's snaps are noise)

EXCLUDED = frozenset({"before", "during"})  # the labels left out of headline numbers


def _lookups(
    injuries: pd.DataFrame,
) -> tuple[dict[tuple[str, int, int], str], set[tuple[str, int, int]]]:
    """(player, season, week) -> report status, and the set of player-weeks on a reserve list."""
    keys = zip(
        injuries["gsis_id"].astype(str),
        injuries["season"].astype(int),
        injuries["week"].astype(int),
        strict=True,
    )
    status: dict[tuple[str, int, int], str] = {}
    reserve: set[tuple[str, int, int]] = set()
    for key, report, roster in zip(
        keys, injuries["report_status"], injuries["roster_status"], strict=True
    ):
        if isinstance(report, str):
            status[key] = report
        if roster == RESERVE:
            reserve.add(key)
    return status, reserve


def _next_week_by_team(history: pd.DataFrame) -> dict[tuple[str, int, int], int]:
    """(team, season, week) -> the team's next game week that season (from who played)."""
    out: dict[tuple[str, int, int], int] = {}
    weeks = (
        history.dropna(subset=["team"]).groupby(["team", "season"])["week"].unique().reset_index()
    )
    for team, season, ws in zip(weeks["team"], weeks["season"], weeks["week"], strict=True):
        ordered = sorted(int(w) for w in ws)
        for cur, nxt in itertools.pairwise(ordered):
            out[(str(team), int(season), cur)] = nxt
    return out


def mark_injury_games(history: pd.DataFrame, injuries: pd.DataFrame | None) -> pd.Series:
    """One label (or None) per history row, aligned to `history.index`.

    history:  gsis_id, season, week, team, snap (one row per game played)
    injuries: gsis_id, season, week, report_status, roster_status, or None
    """
    labels = pd.Series([None] * len(history), index=history.index, dtype=object)
    if history.empty or injuries is None or injuries.empty:
        return labels
    status, reserve = _lookups(injuries)
    next_week = _next_week_by_team(history)

    ordered = history.sort_values(["gsis_id", "season", "week"])
    recent: dict[str, list[float]] = {}  # gsis_id -> snap shares of his earlier games
    for idx, gid, season, week, team, snap in zip(
        ordered.index,
        ordered["gsis_id"],
        ordered["season"],
        ordered["week"],
        ordered["team"],
        ordered["snap"],
        strict=True,
    ):
        gid, season, week = str(gid), int(season), int(week)
        this = status.get((gid, season, week))
        label: str | None = None
        if this in OUT_STATUSES:
            label = "before"
        elif _snap_collapsed(recent.get(gid, []), snap):
            nxt = next_week.get((str(team), season, week))
            if nxt is not None and (
                status.get((gid, season, nxt)) in REPORT_STATUSES or (gid, season, nxt) in reserve
            ):
                label = "during"
        if label is None and this == "Questionable":
            label = "questionable"
        labels.at[idx] = label
        if snap is not None and not pd.isna(snap):
            recent.setdefault(gid, []).append(float(snap))
    return labels


def _snap_collapsed(earlier: list[float], snap: object) -> bool:
    if snap is None or pd.isna(snap) or len(earlier) < MIN_RECENT_GAMES:  # type: ignore[call-overload]
        return False
    normal = float(np.mean(earlier[-RECENT_GAMES:]))
    return normal >= MIN_NORMAL_SNAP and float(snap) < SNAP_DROP * normal  # type: ignore[arg-type]


def excluded(labels: pd.Series) -> pd.Series:
    """True where the game should be left out of headline numbers."""
    return labels.isin(EXCLUDED)
