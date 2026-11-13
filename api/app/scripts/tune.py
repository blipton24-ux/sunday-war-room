"""Tune the model's settings for one position (P4, ADR-054 / ADR-055).

    python -m app.scripts.tune --position WR --out wr.json

Coordinate descent on the **tuning seasons only** (2022-2024): each setting in turn is tried at
every value in its grid and the best is kept if it lowers the average miss on that position's
startable players (all games for K and DEF) by more than MIN_GAIN. Passes repeat until nothing
moves. The check season (2025) is read once, at the end, to report whether the tuned settings
hold up on games they were not tuned on; it never picks a value.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pandas as pd

from app.model import compare, metrics
from app.model.config import SHIPPED, ModelConfig
from app.model.features.context import Extras
from app.model.features.injury_games import excluded
from app.scripts.backtest import load, walk_forward

TUNING = [2022, 2023, 2024]
CHECK = 2025
MIN_GAIN = 0.004  # points of average miss; smaller moves are treated as noise
MAX_PASSES = 3
OFF = 1e9

COMMON: dict[str, list[Any]] = {
    "half_life": [2.0, 3.0, 4.0, 6.0, 9.0, 14.0],
    "prior_games": [1.0, 2.0, 3.0, 5.0, 8.0],
    "prior_games_opener": [None, 1.5, 3.0, 6.0, 10.0],
    "opp_fade_games": [2.0, 4.0, 8.0, 16.0, OFF],
    "opp_clamp": [0.15, 0.25, 0.4],
}
SKILL: dict[str, list[Any]] = {
    "xfp_weight": [0.0, 0.25, 0.5, 0.75, 1.0],
    "td_regression": [0.0, 0.25, 0.5, 0.75, 1.0],
    "def_pass": [False, True],
    "def_run": [False, True],
    "def_schedule_adjust": [False, True],
    "team_offense": [0.0, 0.25, 0.5, 0.75],
    "implied_total": [0.0, 0.3, 0.6, 0.9],
    "game_script": [0.0, 0.005, 0.01, 0.02],
    "rookie_prior": [False, True],
    "home_boost": [0.0, 0.02, 0.04],
    "wind_penalty": [0.0, 0.03, 0.06],
    "rest_effect": [0.0, 0.02, 0.04],
}
ROLE: dict[str, list[Any]] = {
    "usage_trend": [False, True],
    "role_window": [1, 2, 3],
    "role_clamp": [0.0, 0.15, 0.3],
}
GRIDS: dict[str, dict[str, list[Any]]] = {
    "QB": {**COMMON, **SKILL, "def_sack_int": [0.0, 0.15, 0.3]},
    "RB": {**COMMON, **SKILL, **ROLE},
    "WR": {**COMMON, **SKILL, **ROLE},
    "TE": {**COMMON, **SKILL, **ROLE},
    "K": {
        **COMMON,
        "kicker_model": [0.0, 0.3, 0.6, 1.0],
        "home_boost": [0.0, 0.02, 0.04],
        "wind_penalty": [0.0, 0.03, 0.06],
    },
    "DEF": {**COMMON, "defense_model": [0.0, 0.3, 0.6, 1.0, 1.5]},
}


def judged(df: pd.DataFrame, position: str) -> pd.DataFrame:
    """The games a position is judged on: no injury games; startable players where defined."""
    kept = df[~excluded(df["injury_flag"])]
    if position in metrics.STARTABLE_TOP:
        kept = kept[metrics.startable_mask(kept, "naive")]
    return kept


def miss(df: pd.DataFrame, position: str) -> float:
    kept = judged(df, position)
    return float((kept["proj"] - kept["actual"]).abs().mean())


def tune(
    history: pd.DataFrame, extras: Extras, position: str
) -> tuple[ModelConfig, list[dict[str, Any]]]:
    def run(cfg: ModelConfig) -> float:
        return miss(walk_forward(history, TUNING, cfg, extras, positions=(position,)), position)

    best = SHIPPED
    best_miss = run(best)
    log: list[dict[str, Any]] = [{"step": "shipped", "miss": round(best_miss, 4)}]
    for n_pass in range(1, MAX_PASSES + 1):
        moved = False
        for name, grid in GRIDS[position].items():
            current = getattr(best, name)
            trials = {
                value: run(replace(best, **{name: value})) for value in grid if value != current
            }
            value, value_miss = min(trials.items(), key=lambda kv: kv[1])
            if best_miss - value_miss > MIN_GAIN:
                log.append(
                    {"step": f"pass {n_pass}", "setting": name, "from": current, "to": value,
                     "miss": round(value_miss, 4), "gain": round(best_miss - value_miss, 4)}
                )  # fmt: skip
                best, best_miss, moved = replace(best, **{name: value}), value_miss, True
            print(f"{position} pass {n_pass} {name}: {best_miss:.4f}", file=sys.stderr, flush=True)
        if not moved:
            break
    return best, log


def confirm(
    history: pd.DataFrame, extras: Extras, position: str, tuned: ModelConfig
) -> dict[str, Any]:
    """Shipped against tuned, on the tuning seasons and (once) the check season."""
    seasons = [*TUNING, CHECK]
    base = walk_forward(history, seasons, SHIPPED, extras, positions=(position,))
    cand = walk_forward(history, seasons, tuned, extras, positions=(position,))
    paired = compare.pair(base, cand)
    startable = position in metrics.STARTABLE_TOP
    out: dict[str, Any] = {}
    for label, frame in (
        ("tuning", paired[paired["season"].isin(TUNING)]),
        ("check", paired[paired["season"] == CHECK]),
    ):
        for weeks in ("5+", "1-4", None):
            d = compare.slice_diff(frame, startable=startable, weeks=weeks)
            out[f"{label} {weeks or 'all'}"] = {
                "n": d.n, "shipped": round(d.base_mae, 3), "tuned": round(d.cand_mae, 3),
                "change": round(d.change, 3), "low": round(d.low, 3), "high": round(d.high, 3),
                "result": "better" if d.better else "worse" if d.worse else "noise",
            }  # fmt: skip
    return out


def changed(cfg: ModelConfig) -> dict[str, Any]:
    names = [n for grid in GRIDS.values() for n in grid]
    return {
        n: getattr(cfg, n) for n in dict.fromkeys(names) if getattr(cfg, n) != getattr(SHIPPED, n)
    }


def spec(position: str, settings: dict[str, Any]) -> str:
    """The settings as a `--compare` name: `xfp_weight=0.5@WR+...`."""
    return "+".join(f"{k}={v}@{position}" for k, v in settings.items())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--position", required=True, choices=sorted(GRIDS))
    parser.add_argument("--scoring", default="full")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    history, extras = asyncio.run(load(list(range(2021, CHECK + 1)), args.scoring))
    tuned, log = tune(history, extras, args.position)
    settings = changed(tuned)
    result = {
        "position": args.position,
        "scoring": args.scoring,
        "settings": settings,
        "spec": spec(args.position, settings),
        "log": log,
        "confirm": confirm(history, extras, args.position, tuned) if settings else {},
    }
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
