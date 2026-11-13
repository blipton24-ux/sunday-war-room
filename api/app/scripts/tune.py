"""Tune the model's settings for one position, one stage at a time (P4 round 2, ADR-058).

    python -m app.scripts.tune --position RB --stage sweep --jobs 12
    python -m app.scripts.tune --position RB --stage tune  --jobs 12
    python -m app.scripts.tune --position RB --stage check

sweep  every setting in the position's grid, every value, alone against the shipped model, on the
       tuning seasons (2022-2024) only: how much each idea is worth by itself.
tune   coordinate descent on the tuning seasons, settings tried in order of their sweep gain, then a
       refine step that tries values between a winner and its neighbours.
check  opens the check season (2025) once for the tuned settings. Kept if better beyond chance on
       all weeks together on both sets of seasons (ADR-058).

Each stage adds its part to `api/backtest/tuning/<POS>.json` and rewrites the vault page
`docs/Build-Plan/Tuning/<POS>.md`. Only the check stage ever reads 2025.

The search logic (`sweep`, `descend`, `refine`) takes a `Runner`: a function from a list of
settings to one result frame per setting. The command line runs them in parallel processes; the
unit tests pass a fake.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import pickle
import sys
import tempfile
from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import fields, replace
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from app.model import compare, metrics
from app.model.config import SHIPPED, ModelConfig
from app.model.features.context import Extras
from app.model.features.injury_games import excluded

TUNING = [2022, 2023, 2024]
CHECK = 2025
MIN_GAIN = 0.004  # points of average miss; smaller moves are treated as noise
MAX_PASSES = 3
REFINE_ROUNDS = 2
OFF = 1e9  # "never trust the opponent factor" for opp_fade_games

API_DIR = Path(__file__).resolve().parents[2]
RESULTS_DIR = API_DIR / "backtest" / "tuning"
VAULT_DIR = API_DIR.parent / "docs" / "Build-Plan" / "Tuning"

COMMON: dict[str, list[Any]] = {
    "half_life": [2.0, 3.0, 4.0, 6.0, 9.0, 14.0],
    "prior_games": [1.0, 2.0, 3.0, 5.0, 8.0],
    "prior_games_opener": [None, 1.5, 3.0, 6.0, 10.0],
    "opp_fade_games": [2.0, 4.0, 8.0, 16.0, OFF],
    "opp_clamp": [0.15, 0.25, 0.4],
}
SKILL: dict[str, list[Any]] = {
    "xfp_weight": [0.0, 0.25, 0.5, 0.75, 1.0],
    "nfl_xfp_weight": [0.0, 0.25, 0.5, 0.75, 1.0],
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
    "return_discount": [0.0, 0.05, 0.1, 0.2],
}
ROLE: dict[str, list[Any]] = {
    "usage_trend": [False, True],
    "role_window": [1, 2, 3],
    "role_clamp": [0.0, 0.15, 0.3],
    "depth_rank": [0.0, 0.1, 0.25, 0.5, 1.0],
    "teammate_out": [0.0, 0.05, 0.1, 0.2],
}
GRIDS: dict[str, dict[str, list[Any]]] = {
    "QB": {**COMMON, **SKILL, "def_sack_int": [0.0, 0.15, 0.3]},
    "RB": {
        **COMMON,
        **SKILL,
        **ROLE,
        "receiving_half_life": [None, 2.0, 4.0, 6.0, 9.0, 14.0],
        "ypc_regression": [0.0, 0.25, 0.5, 0.75, 1.0],
        "carry_volume": [0.0, 0.25, 0.5, 1.0],
    },
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

Runner = Callable[[Sequence[ModelConfig]], list[pd.DataFrame]]
Log = Callable[[str], None]


def _quiet(_: str) -> None:
    pass


# --------------------------------------------------------------------------- grading
def startable(position: str) -> bool:
    """K and DEF are outside the startable slice, so they are judged on every game."""
    return position in metrics.STARTABLE_TOP


def judged(df: pd.DataFrame, position: str) -> pd.DataFrame:
    """The games a position is judged on: no injury games; startable players where defined."""
    kept = df[~excluded(df["injury_flag"])]
    if startable(position):
        kept = kept[metrics.startable_mask(kept, "naive")]
    return kept


def miss(df: pd.DataFrame, position: str) -> float:
    kept = judged(df, position)
    return float((kept["proj"] - kept["actual"]).abs().mean())


def _diff_dict(d: compare.Diff) -> dict[str, Any]:
    return {
        "n": d.n, "shipped": round(d.base_mae, 4), "tuned": round(d.cand_mae, 4),
        "change": round(d.change, 4), "low": round(d.low, 4), "high": round(d.high, 4),
        "result": "better" if d.better else "worse" if d.worse else "noise",
    }  # fmt: skip


def slices(paired: pd.DataFrame, position: str) -> dict[str, dict[str, Any]]:
    """The change on all weeks, weeks 5+ and weeks 1-4."""
    return {
        label: _diff_dict(compare.slice_diff(paired, startable=startable(position), weeks=weeks))
        for label, weeks in (("all", None), ("5+", "5+"), ("1-4", "1-4"))
    }


# --------------------------------------------------------------------------- search
def changed(cfg: ModelConfig, grid: dict[str, list[Any]]) -> dict[str, Any]:
    return {n: getattr(cfg, n) for n in grid if getattr(cfg, n) != getattr(SHIPPED, n)}


def sweep(
    run: Runner, position: str, grid: dict[str, list[Any]], log: Log = _quiet
) -> dict[str, Any]:
    """Every value of every setting, alone against shipped, on the tuning seasons."""
    trials = [(name, value) for name, values in grid.items() for value in values]
    trials = [(n, v) for n, v in trials if v != getattr(SHIPPED, n)]
    frames = run([SHIPPED, *(replace(SHIPPED, **{n: v}) for n, v in trials)])
    base, rest = frames[0], frames[1:]
    rows = []
    for (name, value), frame in zip(trials, rest, strict=True):
        rows.append(
            {"setting": name, "value": value, **slices(compare.pair(base, frame), position)}
        )
        log(f"{position} sweep {name}={value}: {rows[-1]['all']['change']:+.4f}")
    best: dict[str, float] = {}
    for row in rows:
        best[row["setting"]] = min(best.get(row["setting"], 0.0), row["all"]["change"])
    order = sorted(grid, key=lambda n: best.get(n, 0.0))
    return {"shipped_miss": round(miss(base, position), 4), "rows": rows, "order": order}


def _best_move(
    run: Runner, position: str, best: ModelConfig, name: str, values: Sequence[Any]
) -> tuple[Any, float]:
    frames = run([replace(best, **{name: v}) for v in values])
    misses = [miss(f, position) for f in frames]
    i = min(range(len(values)), key=misses.__getitem__)
    return values[i], misses[i]


def descend(
    run: Runner,
    position: str,
    grid: dict[str, list[Any]],
    order: Sequence[str],
    log: Log = _quiet,
) -> tuple[ModelConfig, float, list[dict[str, Any]]]:
    """Coordinate descent from the shipped settings: each setting in `order`, every value, keep
    the best if it lowers the miss by more than MIN_GAIN; repeat until a pass changes nothing."""
    best = SHIPPED
    best_miss = miss(run([best])[0], position)
    steps: list[dict[str, Any]] = [{"step": "shipped", "miss": round(best_miss, 4)}]
    for n_pass in range(1, MAX_PASSES + 1):
        moved = False
        for name in order:
            current = getattr(best, name)
            values = [v for v in grid[name] if v != current]
            if not values:
                continue
            value, value_miss = _best_move(run, position, best, name, values)
            if best_miss - value_miss > MIN_GAIN:
                steps.append(
                    {"step": f"pass {n_pass}", "setting": name, "from": current, "to": value,
                     "miss": round(value_miss, 4), "gain": round(best_miss - value_miss, 4)}
                )  # fmt: skip
                best, best_miss, moved = replace(best, **{name: value}), value_miss, True
            log(f"{position} pass {n_pass} {name}: {best_miss:.4f}")
        if not moved:
            break
    return best, best_miss, steps


def _is_number(v: Any) -> bool:
    return isinstance(v, int | float) and not isinstance(v, bool) and v != OFF


def between(name: str, value: Any, tried: Sequence[Any]) -> list[Any]:
    """Values halfway between `value` and its nearest tried neighbours on each side. Only plain
    numbers are refined: not on/off settings, not None, not the OFF sentinel."""
    if not _is_number(value):
        return []
    numbers = sorted({v for v in tried if _is_number(v)})
    lower = [v for v in numbers if v < value]
    upper = [v for v in numbers if v > value]
    whole = isinstance(getattr(SHIPPED, name), int)
    out: list[Any] = []
    for other in (lower[-1] if lower else None, upper[0] if upper else None):
        if other is None:
            continue
        mid = round((value + other) / 2) if whole else round((value + other) / 2, 4)
        if mid not in numbers and mid != value:
            out.append(mid)
    return out


def refine(
    run: Runner,
    position: str,
    grid: dict[str, list[Any]],
    start: ModelConfig,
    start_miss: float,
    log: Log = _quiet,
) -> tuple[ModelConfig, float, list[dict[str, Any]]]:
    """Try values between each tuned number and its neighbours, keeping gains over MIN_GAIN."""
    best, best_miss = start, start_miss
    tried = {name: list(values) for name, values in grid.items()}
    steps: list[dict[str, Any]] = []
    for n_round in range(1, REFINE_ROUNDS + 1):
        moved = False
        for name in grid:
            current = getattr(best, name)
            values = between(name, current, tried[name])
            if not values:
                continue
            tried[name].extend(values)
            value, value_miss = _best_move(run, position, best, name, values)
            if best_miss - value_miss > MIN_GAIN:
                steps.append(
                    {"step": f"refine {n_round}", "setting": name, "from": current, "to": value,
                     "miss": round(value_miss, 4), "gain": round(best_miss - value_miss, 4)}
                )  # fmt: skip
                best, best_miss, moved = replace(best, **{name: value}), value_miss, True
            log(f"{position} refine {n_round} {name}: {best_miss:.4f}")
        if not moved:
            break
    return best, best_miss, steps


def check(run_all: Runner, position: str, tuned: ModelConfig) -> dict[str, Any]:
    """Shipped against tuned on the tuning seasons and (once) the check season. `run_all` covers
    both sets of seasons."""
    base, cand = run_all([SHIPPED, tuned])
    paired = compare.pair(base, cand)
    tuning = slices(paired[paired["season"].isin(TUNING)], position)
    check_season = slices(paired[paired["season"] == CHECK], position)
    kept = tuning["all"]["result"] == "better" and check_season["all"]["result"] == "better"
    return {"tuning": tuning, "check": check_season, "kept": kept}


# --------------------------------------------------------------------------- settings as text
def spec(position: str, settings: dict[str, Any]) -> str:
    """The settings as a `--compare` name: `xfp_weight=0.5@WR+...`."""
    return "+".join(f"{k}={v}@{position}" for k, v in settings.items())


def from_settings(settings: dict[str, Any]) -> ModelConfig:
    unknown = set(settings) - {f.name for f in fields(ModelConfig)}
    if unknown:
        raise SystemExit(f"Unknown settings in the saved results: {sorted(unknown)}")
    return replace(SHIPPED, **settings)


# --------------------------------------------------------------------------- parallel runs
_DATA: dict[str, Any] = {}


def _init_worker(path: str) -> None:
    with open(path, "rb") as fh:
        _DATA.update(pickle.load(fh))


def _walk(job: tuple[ModelConfig, str, tuple[int, ...]]) -> pd.DataFrame:
    from app.scripts.backtest import walk_forward

    cfg, position, seasons = job
    history: pd.DataFrame = _DATA["history"]
    extras: Extras = _DATA["extras"]
    frame = walk_forward(history, list(seasons), cfg, extras, positions=(position,))
    columns = ["gsis_id", "position", "season", "week", "actual", "naive", "injury_flag", "proj"]
    return frame[columns]


def make_runner(pool: ProcessPoolExecutor | None, position: str, seasons: Sequence[int]) -> Runner:
    def run(configs: Sequence[ModelConfig]) -> list[pd.DataFrame]:
        jobs = [(cfg, position, tuple(seasons)) for cfg in configs]
        if pool is None:
            return [_walk(job) for job in jobs]
        return list(pool.map(_walk, jobs))

    return run


# --------------------------------------------------------------------------- files
def write_results(position: str, results: dict[str, Any]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    text = json.dumps(results, indent=2, default=str)
    unix = "\n"  # the repo uses LF; Windows would otherwise write CRLF
    (RESULTS_DIR / f"{position}.json").write_text(text + unix, encoding="utf-8", newline=unix)
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    page = render(position, results)
    (VAULT_DIR / f"{position}.md").write_text(page, encoding="utf-8", newline=unix)


def _cell(d: dict[str, Any]) -> str:
    return f"{d['change']:+.3f} ({d['low']:+.3f} to {d['high']:+.3f}) {d['result']}"


def render(position: str, results: dict[str, Any]) -> str:
    """The vault page for one position (generated; commentary goes in the ledger)."""
    judged_on = "startable players" if startable(position) else "every game"
    lines = [
        "---",
        f'title: "Round 2 tuning: {position}"',
        f"date: {results.get('date', '')}",
        "tags: [build-plan, p4, model, tuning]",
        "---",
        f"# Round 2 tuning: {position}",
        "",
        f"Generated by `python -m app.scripts.tune --position {position}` "
        "([ADR-058](../../Decisions/ADR-058-P4-Round-2-One-Position-At-A-Time.md)). "
        f"Full PPR, {judged_on}, injury games left out. Change in average miss in points against "
        "the shipped model (negative is better), with the 95% interval. What the numbers mean and "
        "what was decided: [Model Experiments](../Model-Experiments.md).",
        "",
    ]
    sweep_part = results.get("sweep")
    if sweep_part:
        lines += [
            "## Sweep: each setting alone, tuning seasons 2022-2024",
            "",
            f"Shipped model's average miss: **{sweep_part['shipped_miss']:.4f}**. Shipped values "
            "are not repeated; rows are best first.",
            "",
            "| Setting | Value | All weeks | Weeks 5+ | Weeks 1-4 |",
            "|---|---|---|---|---|",
        ]
        for row in sorted(sweep_part["rows"], key=lambda r: r["all"]["change"]):
            lines.append(
                f"| `{row['setting']}` | {row['value']} | {_cell(row['all'])} "
                f"| {_cell(row['5+'])} | {_cell(row['1-4'])} |"
            )
        lines.append("")
    tune_part = results.get("tune")
    if tune_part:
        lines += [
            "## Tune: settings combined, tuning seasons 2022-2024",
            "",
            "Settings tried in order of their sweep gain; a move is kept only if it lowers the "
            f"miss by more than {MIN_GAIN} points.",
            "",
            "| Step | Setting | From | To | Miss | Gain |",
            "|---|---|---|---|---|---|",
        ]
        for s in tune_part["steps"]:
            if s["step"] == "shipped":
                lines.append(f"| shipped | | | | {s['miss']:.4f} | |")
            else:
                lines.append(
                    f"| {s['step']} | `{s['setting']}` | {s['from']} | {s['to']} "
                    f"| {s['miss']:.4f} | {s['gain']:.4f} |"
                )
        settings = ", ".join(f"`{k}` {v}" for k, v in tune_part["settings"].items()) or "none"
        lines += ["", f"Tuned settings: {settings}.", ""]
    check_part = results.get("check")
    if check_part:
        verdict = "**kept**" if check_part["kept"] else "**not kept**"
        lines += [
            "## Check: tuned against shipped",
            "",
            "| Seasons | All weeks | Weeks 5+ | Weeks 1-4 |",
            "|---|---|---|---|",
        ]
        for label, key in (("Tuning 2022-2024", "tuning"), ("Check 2025", "check")):
            part = check_part[key]
            lines.append(
                f"| {label} | {_cell(part['all'])} | {_cell(part['5+'])} | {_cell(part['1-4'])} |"
            )
        lines += [
            "",
            f"Verdict: {verdict} (better beyond chance on all weeks, on both sets of seasons).",
            "",
        ]
    earlier = results.get("earlier_checks", [])
    if earlier:
        lines += [
            f"**The check season has been opened {len(earlier) + bool(check_part)} times for this "
            "position in round 2**; earlier settings were re-tuned after a look at 2025, so the "
            "latest check is weaker evidence than a first look. Earlier verdicts: "
            + ", ".join("kept" if c["kept"] else "not kept" for c in earlier)
            + ".",
            "",
        ]
    lines.append(
        "Related: [Tuning index](README.md) · [Model Experiments](../Model-Experiments.md) · "
        "[P4 Build Plan](../P4-Build-Plan.md)"
    )
    return "\n".join(lines) + "\n"


def merge_sweep(
    old: dict[str, Any] | None, new: dict[str, Any], grid: dict[str, list[Any]]
) -> dict[str, Any]:
    """Add newly swept settings to an earlier sweep (each row is one setting alone against the
    shipped model, so rows from separate runs compare like for like). Settings swept again
    replace their old rows; the order is recomputed over every setting."""
    if old is None:
        return {**new, "order": [n for n in new["order"] if n in grid]}
    if abs(old["shipped_miss"] - new["shipped_miss"]) > 1e-9:
        raise SystemExit("The shipped model's miss changed since the last sweep: re-run it whole.")
    swept = {r["setting"] for r in new["rows"]} | set(new["order"])
    rows = [r for r in old["rows"] if r["setting"] not in swept] + new["rows"]
    best: dict[str, float] = {}
    for row in rows:
        best[row["setting"]] = min(best.get(row["setting"], 0.0), row["all"]["change"])
    names = [n for n in grid if n in best or n in old["order"] or n in new["order"]]
    order = sorted(names, key=lambda n: best.get(n, 0.0))
    return {"shipped_miss": new["shipped_miss"], "rows": rows, "order": order}


def retire_check(results: dict[str, Any]) -> None:
    """A re-run after the check season was opened keeps that check on record (ADR-058): the
    page then shows how many times 2025 has been looked at for this position."""
    old = results.pop("check", None)
    if old is not None:
        results.setdefault("earlier_checks", []).append(old)


# --------------------------------------------------------------------------- command line
def main() -> None:
    from app.scripts.backtest import load

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--position", required=True, choices=sorted(GRIDS))
    parser.add_argument("--stage", required=True, choices=("sweep", "tune", "check"))
    parser.add_argument("--scoring", default="full")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument(
        "--settings",
        help="sweep only these comma-separated settings and add them to the saved sweep",
    )
    args = parser.parse_args()
    position, grid = args.position, GRIDS[args.position]
    if position in dict(SHIPPED.overrides):
        # Shipped per-position settings would override every value tried here (ADR-059).
        raise SystemExit(
            f"{position} already ships its own settings; re-tuning it needs the tuner to start "
            "from SHIPPED.for_position(position) first."
        )
    if args.settings:
        if args.stage != "sweep":
            raise SystemExit("--settings is for --stage sweep only")
        unknown = set(args.settings.split(",")) - set(grid)
        if unknown:
            raise SystemExit(f"Not in the {position} grid: {sorted(unknown)}")

    def log(text: str) -> None:
        print(text, file=sys.stderr, flush=True)

    path = RESULTS_DIR / f"{position}.json"
    results: dict[str, Any] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if args.stage == "tune" and "sweep" not in results:
        raise SystemExit("Run --stage sweep first: tune uses its order.")
    if args.stage == "check" and "tune" not in results:
        raise SystemExit("Run --stage tune first.")
    if args.stage == "check" and "check" in results:
        raise SystemExit("The check season was already opened for these settings (ADR-058).")

    history, extras = asyncio.run(load(list(range(2021, CHECK + 1)), args.scoring))
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as fh:
        pickle.dump({"history": history, "extras": extras}, fh)
        data_path = fh.name
    _init_worker(data_path)
    pool = (
        ProcessPoolExecutor(args.jobs, initializer=_init_worker, initargs=(data_path,))
        if args.jobs > 1
        else None
    )
    try:
        results.update(
            {"position": position, "scoring": args.scoring, "date": date.today().isoformat()}
        )
        if args.stage == "sweep":
            names = args.settings.split(",") if args.settings else list(grid)
            part = sweep(make_runner(pool, position, TUNING), position,
                         {n: grid[n] for n in names}, log)  # fmt: skip
            results["sweep"] = merge_sweep(results.get("sweep"), part, grid)
            results.pop("tune", None)
            retire_check(results)
        elif args.stage == "tune":
            run = make_runner(pool, position, TUNING)
            tuned, tuned_miss, steps = descend(run, position, grid, results["sweep"]["order"], log)
            tuned, tuned_miss, more = refine(run, position, grid, tuned, tuned_miss, log)
            settings = changed(tuned, grid)
            results["tune"] = {
                "settings": settings,
                "spec": spec(position, settings),
                "miss": round(tuned_miss, 4),
                "steps": steps + more,
            }
            retire_check(results)
        else:
            tuned = from_settings(results["tune"]["settings"])
            results["check"] = check(make_runner(pool, position, [*TUNING, CHECK]), position, tuned)
        write_results(position, results)
        summary = {k: v for k, v in results.items() if k != "sweep"}
        print(json.dumps(summary, indent=2, default=str))
    finally:
        if pool is not None:
            pool.shutdown()
        Path(data_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
