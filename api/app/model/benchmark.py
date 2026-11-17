"""Sleeper's past weekly projections as an outside benchmark (ADR-066). Benchmark only: never a
model input, never stored in the database, never committed (the cache folder is git-ignored and
the numbers are Rotowire's, licensed to Sleeper). Reports show only totals.

The endpoint is the one Sleeper's own app uses; it is not in Sleeper's documented API, so it may
change. One request per season, week and position, a second apart.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

URL = "https://api.sleeper.app/projections/nfl/{season}/{week}"
POSITIONS = ("QB", "RB", "WR", "TE")
POINTS = {"half": "pts_half_ppr", "full": "pts_ppr", "standard": "pts_std"}
COLUMNS = ["sleeper_id", "season", "week", *POINTS]
DEFAULT_CACHE = Path(__file__).resolve().parents[2] / "benchmarks" / "sleeper"
PAUSE_SECONDS = 1.0


def parse(raw: Iterable[Mapping[str, Any]], season: int, week: int) -> pd.DataFrame:
    """One row per player with a projection: Sleeper's player id and points in each format.
    Players listed without stats (on a reserve list, say) have no projection and are left out."""
    rows = []
    for item in raw:
        stats = item.get("stats") or {}
        if stats.get(POINTS["half"]) is None:
            continue
        points = {fmt: float(stats.get(key) or 0.0) for fmt, key in POINTS.items()}
        rows.append(
            {"sleeper_id": str(item["player_id"]), "season": season, "week": week, **points}
        )
    return pd.DataFrame(rows, columns=COLUMNS)


def fetch_season(
    season: int,
    weeks: Sequence[int] = tuple(range(1, 19)),
    get: Callable[[str, dict[str, str]], Any] | None = None,
    pause: float = PAUSE_SECONDS,
) -> pd.DataFrame:
    """Every projection for one season. `get(url, params)` returns parsed JSON (for tests)."""
    if get is None:
        client = httpx.Client(timeout=30, headers={"User-Agent": "sunday-war-room-benchmark"})

        def get(url: str, params: dict[str, str]) -> Any:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    frames = []
    for week in weeks:
        for position in POSITIONS:
            raw = get(URL.format(season=season, week=week),
                      {"season_type": "regular", "position[]": position})  # fmt: skip
            frames.append(parse(raw, season, week))
            time.sleep(pause)
    out = pd.concat(frames, ignore_index=True)
    return out.drop_duplicates(["sleeper_id", "week"]).reset_index(drop=True)


def load(seasons: Sequence[int], cache: Path = DEFAULT_CACHE) -> pd.DataFrame:
    """The cached seasons that exist (empty if none have been fetched)."""
    files = [cache / f"{s}.csv" for s in seasons if (cache / f"{s}.csv").exists()]
    if not files:
        return pd.DataFrame(columns=COLUMNS)
    out = pd.concat([pd.read_csv(f, dtype={"sleeper_id": str}) for f in files], ignore_index=True)
    return out


def attach(paired: pd.DataFrame, sleeper: pd.DataFrame, crosswalk: Mapping[str, str],
           scoring: str) -> pd.DataFrame:  # fmt: skip
    """`paired` with a `sleeper` column (points in `scoring`) where Sleeper had a projection.
    `crosswalk`: Sleeper player id -> gsis id (the players table)."""
    s = sleeper.assign(gsis_id=sleeper["sleeper_id"].map(crosswalk)).dropna(subset=["gsis_id"])
    s = s.drop_duplicates(["gsis_id", "season", "week"])
    s = s[["gsis_id", "season", "week", scoring]].rename(columns={scoring: "sleeper"})
    return paired.merge(s, on=["gsis_id", "season", "week"], how="left")
