"""Grade the machine-learning model against model 1.0.0 on the four test seasons (P4 step 7).

    python -m app.scripts.evaluate_ml --cache ml.pkl   # trains, then reports
    python -m app.scripts.evaluate_ml --cache ml.pkl --report ML-Evaluation-Report.md

Walk-forward season by season (ADR-061), retrained every 4 weeks inside each test season
(ADR-065; `ml/walk_forward.py`). Both models are graded on exactly the same player-games: the
four skill positions (kickers and defenses keep the 1.0.0 method in 2.0.0, P4 step 12). The
ML projections are cached (`--cache`) because training takes about an hour; delete the file
to retrain. Sleeper's projections are added as an outside benchmark when they have been fetched
(`python -m app.scripts.fetch_sleeper_benchmark`, ADR-066). The current season is never
read here: it is the one look before shipping (step 11).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import select

from app.db.models import Player
from app.db.session import get_engine, get_sessionmaker
from app.model import benchmark, compare, metrics
from app.model.distribution import apply_range, load_calibration
from app.model.ml.data import ModelData, load_model_data
from app.model.ml.features import SKILL
from app.model.ml.train import training_table
from app.model.ml.walk_forward import RETRAIN_WEEKS, ml_walk_forward
from app.model.projection import MODEL_VERSION
from app.scripts import backtest

FORMATS = ("half", "full", "standard")
KEY = ["gsis_id", "season", "week"]
# The removed model 1.1.0's published numbers (Projection Model spec), half PPR, held-out 2025.
V110 = {"rb_mae_2025": 4.07, "rb_startable_5plus_change_2025": -0.172}


def ml_projections(
    first: int, seasons: Sequence[int], cache: Path | None
) -> dict[str, pd.DataFrame]:
    if cache is not None and cache.exists():
        frames: dict[str, pd.DataFrame] = pd.read_pickle(cache).to_dict()
        return frames

    async def _load() -> ModelData:
        async with get_sessionmaker()() as db:
            data = await load_model_data(db, list(range(first, max(seasons) + 1)))
        await get_engine().dispose()
        return data

    started = time.time()
    data = asyncio.run(_load())
    table = training_table(data, range(first, max(seasons) + 1))
    out = ml_walk_forward(
        table, first, seasons, {f: backtest.SCORING[f] for f in FORMATS},
        progress=lambda m: print(f"{(time.time() - started) / 60:5.1f} min  {m}", file=sys.stderr,
                                 flush=True),
    )  # fmt: skip
    if cache is not None:
        pd.Series(out).to_pickle(cache)
    return out


def paired_frames(scoring: str, ml: pd.DataFrame, seasons: Sequence[int]) -> pd.DataFrame:
    """1.0.0 and the ML model on the same skill-position player-games."""
    history = asyncio.run(backtest.load(list(range(min(seasons) - 1, max(seasons) + 1)), scoring))
    base = backtest.walk_forward(history, list(seasons), positions=SKILL)
    rows = base.merge(ml[[*KEY, "proj"]], on=KEY, how="inner", suffixes=("", "_ml"))
    cand = rows.drop(columns="proj").rename(columns={"proj_ml": "proj"})
    return compare.pair(rows.drop(columns="proj_ml"), cand).assign(
        _graded=len(rows), _base_rows=len(base), _ml_rows=len(ml)
    )


def sleeper_crosswalk() -> dict[str, str]:
    """Sleeper player id -> gsis id, from the players table."""

    async def _load() -> dict[str, str]:
        async with get_sessionmaker()() as db:
            rows = await db.execute(
                select(Player.sleeper_id, Player.gsis_id).where(
                    Player.sleeper_id.is_not(None), Player.gsis_id.is_not(None)
                )
            )
            out = {str(s): str(g) for s, g in rows.all()}
        await get_engine().dispose()
        return out

    return asyncio.run(_load())


# --------------------------------------------------------------------------- report
def _mae(g: pd.DataFrame, col: str) -> float:
    return float((g[col] - g["actual"]).abs().mean()) if len(g) else float("nan")


def _rank(g: pd.DataFrame, col: str) -> float:
    return float(metrics.grade(g.assign(proj=g[col]))["rank_corr"]) if len(g) else float("nan")


def _slice(p: pd.DataFrame, injury_games: bool = False) -> pd.DataFrame:
    keep = p["startable"] if injury_games else p["startable"] & ~p["left_out"]
    return p[keep]


def _diff_cells(d: compare.Diff) -> str:
    return f"{d.change:+.3f} | {d.low:+.3f} to {d.high:+.3f} | {compare._flag(d)}"


def format_section(name: str, p: pd.DataFrame) -> list[str]:
    ev = compare.ship_evidence(p)
    verdict = compare.ship_rule(ev)
    s = _slice(p)
    lines = [
        f"## {name} PPR",
        "",
        f"{int(p['_graded'].iloc[0]):,} player-games graded ({int(p['_base_rows'].iloc[0]):,} in "
        f"1.0.0's backtest, {int(p['_ml_rows'].iloc[0]):,} projected by the ML model); "
        f"{int(p['left_out'].sum()):,} left out for injuries.",
        "",
        "**Ship rule: " + ("passes.**" if verdict.kept else "does not pass.**"),
        *[f"- {r}" for r in verdict.reasons],
        "",
        "Startable players, all weeks, injury games left out. Average miss in points.",
        "",
        "| Seasons | Games | Season average | 1.0.0 | ML | Change | 95% interval | Result |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for label, d, g in [
        *[(str(k), v, s[s["season"] == k]) for k, v in ev.seasons.items()],
        ("**All four**", ev.pooled, s),
    ]:
        lines.append(f"| {label} | {d.n:,} | {_mae(g, 'naive'):.3f} | {d.base_mae:.3f} "
                     f"| {d.cand_mae:.3f} | {_diff_cells(d)} |")  # fmt: skip
    lines += ["", "| Position (four seasons) | Games | Season average | 1.0.0 | ML | Change "
              "| 95% interval | Result | Rank corr 1.0.0 | Rank corr ML |",
              "|---|---|---|---|---|---|---|---|---|---|"]  # fmt: skip
    for pos, d in ev.positions.items():
        g = s[s["position"] == pos]
        lines.append(f"| {pos} | {d.n:,} | {_mae(g, 'naive'):.3f} | {d.base_mae:.3f} "
                     f"| {d.cand_mae:.3f} | {_diff_cells(d)} | {_rank(g, 'proj_base'):.3f} "
                     f"| {_rank(g, 'proj_cand'):.3f} |")  # fmt: skip
    lines += ["", "| Other slices (four seasons) | Games | 1.0.0 | ML | Change | 95% interval "
              "| Result |", "|---|---|---|---|---|---|---|"]  # fmt: skip
    for label, kw in (
        ("Startable, weeks 1-4", {"startable": True, "weeks": "1-4"}),
        ("Startable, weeks 5+", {"startable": True, "weeks": "5+"}),
        ("Startable, **everything counted**", {"startable": True, "weeks": None,
                                               "include_injury_games": True}),
        ("All skill players, all weeks", {"startable": False, "weeks": None}),
    ):  # fmt: skip
        d = compare.slice_diff(p, **kw)
        lines.append(f"| {label} | {d.n:,} | {d.base_mae:.3f} | {d.cand_mae:.3f} "
                     f"| {_diff_cells(d)} |")  # fmt: skip
    lines += ["", f"Rank accuracy (Spearman per position-week, startable): 1.0.0 "
              f"{_rank(s, 'proj_base'):.3f}, ML {_rank(s, 'proj_cand'):.3f}, season average "
              f"{_rank(s, 'naive'):.3f}.", ""]  # fmt: skip
    return lines


def coverage_section(paired: dict[str, pd.DataFrame]) -> list[str]:
    """How often the actual score lands in the 80% range, using 1.0.0's fitted ranges on both
    models (the ML model's own ranges are fitted in P4 step 8)."""
    cal = load_calibration(MODEL_VERSION)
    lines = [
        "## Range coverage",
        "",
        "Share of actual scores inside the 10th-90th percentile range (target about 80%), all "
        "skill players and weeks, everything counted. Both columns use **1.0.0's ranges** "
        "(fitted in half PPR); the ML model's own ranges come in step 8, so its column only shows "
        "how far off borrowed ranges are.",
        "",
        "| Format | Position | 1.0.0 | ML with 1.0.0's ranges |",
        "|---|---|---|---|",
    ]
    for fmt, p in paired.items():
        for pos, g in p.groupby("position"):
            cells = []
            for col in ("proj_base", "proj_cand"):
                lo_hi = [apply_range(x, str(pos), cal) for x in g[col]]
                lo = pd.Series([r[0] for r in lo_hi], index=g.index)
                hi = pd.Series([r[2] for r in lo_hi], index=g.index)
                cells.append(f"{((g['actual'] >= lo) & (g['actual'] <= hi)).mean():.1%}")
            lines.append(f"| {fmt} | {pos} | {cells[0]} | {cells[1]} |")
    return [*lines, ""]


def benchmark_section(half: pd.DataFrame) -> list[str]:
    rb = half[(half["season"] == 2025) & (half["position"] == "RB")]
    d = compare.slice_diff(rb, startable=True, weeks="5+")
    return [
        "## Benchmarks",
        "",
        "Season average and 1.0.0 are in every table above. The removed model 1.1.0 (running "
        "backs only) published two numbers on held-out 2025, half PPR:",
        "",
        "| Number | 1.0.0 | 1.1.0 (published) | ML |",
        "|---|---|---|---|",
        f"| All running backs, average miss | {_mae(rb, 'proj_base'):.2f} "
        f"| {V110['rb_mae_2025']:.2f} | {_mae(rb, 'proj_cand'):.2f} |",
        f"| Startable running backs, weeks 5+, change against 1.0.0 | 0 "
        f"| {V110['rb_startable_5plus_change_2025']:+.3f} | {d.change:+.3f} |",
        "",
        "1.1.0's 4.07 counted every game; the ML column here does too.",
        "",
    ]


def sleeper_section(paired: dict[str, pd.DataFrame]) -> list[str]:
    """ADR-066: Sleeper's own projections (Rotowire's) on the player-games they cover."""
    if not any("sleeper" in p.columns for p in paired.values()):
        return []
    lines = [
        "## Outside benchmark: Sleeper's projections",
        "",
        "Sleeper's past weekly projections (supplied to Sleeper by Rotowire; "
        "[ADR-066](../Decisions/ADR-066-P4-Sleeper-Projections-As-A-Local-Benchmark.md)), on the "
        "startable player-games Sleeper projected, injury games left out. Benchmark only, never a "
        "model input. Average miss in points, and rank accuracy.",
        "",
        "| Format | Slice | Games | 1.0.0 | ML | Sleeper | Rank 1.0.0 | Rank ML | Rank Sleeper |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for fmt, p in paired.items():
        s = _slice(p)
        s = s[s["sleeper"].notna()]
        slices = [*[(str(k), g) for k, g in s.groupby("season")], ("**All four**", s),
                  *[(str(k), g) for k, g in s.groupby("position")]]  # fmt: skip
        for label, g in slices:
            lines.append(f"| {fmt} | {label} | {len(g):,} | {_mae(g, 'proj_base'):.3f} "
                         f"| {_mae(g, 'proj_cand'):.3f} | {_mae(g, 'sleeper'):.3f} "
                         f"| {_rank(g, 'proj_base'):.3f} | {_rank(g, 'proj_cand'):.3f} "
                         f"| {_rank(g, 'sleeper'):.3f} |")  # fmt: skip
    return [*lines, ""]


def render(paired: dict[str, pd.DataFrame], seasons: Sequence[int], first: int) -> str:
    lines = [
        "---",
        'title: "ML Evaluation Report (P4 step 7)"',
        f"date: {date.today().isoformat()}",
        "tags: [model, machine-learning, backtest, p4]",
        "---",
        "# ML evaluation: the machine-learning model against 1.0.0",
        "",
        f"Generated by `python -m app.scripts.evaluate_ml`. Test seasons {seasons[0]}-{seasons[-1]}"
        f", walk-forward: each trained on {first} to the season before, retrained before weeks "
        f"{', '.join(map(str, RETRAIN_WEEKS))} with that season's earlier games added "
        "([ADR-065](../Decisions/ADR-065-P4-Retrain-Every-Four-Weeks-In-Testing.md)). Settings "
        "are chosen inside the training seasons only. Startable: each week's top 15 QB and TE and "
        "top 36 RB and WR by season average, so both models are graded on the same players. "
        'Negative change = the ML model misses less; the result is "better" or "worse" only '
        "when the whole 95% interval (paired bootstrap over weeks) is on one side of zero. The "
        "ship rule ([ADR-061](../Decisions/ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md)) "
        "also needs the 2026 weeks, looked at once in step 11. Kickers and defenses are not "
        "graded here (1.0.0 method until step 12). Rest-of-season projections still use the "
        "1.0.0 method.",
        "",
    ]
    for fmt, p in paired.items():
        lines += format_section(fmt.capitalize(), p)
    lines += coverage_section(paired)
    lines += benchmark_section(paired["half"])
    lines += sleeper_section(paired)
    lines += [
        "Related: [P4 Build Plan](P4-Build-Plan.md) · [ML Training Report](ML-Training-Report.md)"
        " · [Backtest Report](Backtest-Report.md) · "
        "[ADR-061](../Decisions/ADR-061-P4-How-The-ML-Model-Is-Tested-And-Shipped.md)",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", type=int, default=2016, help="first training season")
    parser.add_argument("--test", type=int, nargs="+", default=[2022, 2023, 2024, 2025])
    parser.add_argument("--cache", type=Path, help="ML projections cache (pickle)")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    seasons = sorted(args.test)
    ml = ml_projections(args.first, seasons, args.cache)
    paired = {fmt: paired_frames(fmt, ml[fmt], seasons) for fmt in FORMATS}
    sleeper = benchmark.load(seasons)
    if not sleeper.empty:
        crosswalk = sleeper_crosswalk()
        paired = {fmt: benchmark.attach(p, sleeper, crosswalk, fmt) for fmt, p in paired.items()}
    text = render(paired, seasons, args.first)
    print(text)
    if args.report:
        args.report.write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
