"""Walk-forward backtest of the projection model; fits and writes the range calibration.

    python -m app.scripts.backtest                       # report only
    python -m app.scripts.backtest --write-calibration   # also refresh app/model/calibration.json
    python -m app.scripts.backtest --report ../docs/Build-Plan/Backtest-Report.md

Walk-forward: each week is projected using only games before it, exactly as it would have been
live. Ranges are fit on the earlier test seasons and their coverage is checked on the last,
held-out season. Needs nflverse data in the database (the ingest_nflverse job, full=True).
Injury and depth-chart data aren't historical, so the backtest measures the model without them.

The report also checks rest-of-season projections (app/model/rest_of_season.py): from a few
points in the held-out season, each player's projected points for the rest of the regular
season vs what he actually scored, per remaining week.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from app.db.session import get_engine, get_sessionmaker
from app.model import metrics
from app.model.distribution import CALIBRATION_FILE, apply_range, fit_calibration
from app.model.projection import MODEL_VERSION, Context, project_week
from app.model.rest_of_season import Horizon, project_rest_of_season
from app.model.scoring import REFERENCE_RULES
from app.services.history import load_stat_rows, scored_history


def walk_forward(history: pd.DataFrame, seasons: list[int]) -> pd.DataFrame:
    """Projection vs actual for every player-game in `seasons`, plus a naive baseline."""
    frames = []
    for season in seasons:
        for week in sorted(history.loc[history["season"] == season, "week"].unique()):
            actual = history[(history["season"] == season) & (history["week"] == week)]
            targets = actual[["gsis_id", "position", "team", "opponent"]]
            proj = project_week(history, targets, Context(season, int(week)), calibration=None)
            merged = proj[["gsis_id", "position", "points"]].merge(
                actual[["gsis_id", "points"]].rename(columns={"points": "actual"}), on="gsis_id"
            )
            merged["naive"] = naive_projection(history, merged["gsis_id"], season, int(week))
            merged["season"], merged["week"] = season, int(week)
            frames.append(merged.rename(columns={"points": "proj"}))
    return pd.concat(frames, ignore_index=True)


def naive_projection(history: pd.DataFrame, ids: pd.Series, season: int, week: int) -> list[float]:
    """The bar to beat: plain season-to-date average (last season's if no games yet)."""
    before = history[(history["season"] == season) & (history["week"] < week)]
    last = history[history["season"] == season - 1]
    cur_mean = before.groupby("gsis_id")["points"].mean()
    last_mean = last.groupby("gsis_id")["points"].mean()
    return [float(cur_mean.get(i, last_mean.get(i, 0.0))) for i in ids]


ROS_FROM_WEEKS = (4, 8, 12)
ROS_LAST_WEEK = 17
ROS_MIN_GAMES = 3  # players with this many games before the start point are evaluated


def schedule_from_history(history: pd.DataFrame, season: int) -> dict[int, dict[str, str]]:
    """week -> {team: opponent}, rebuilt from who played whom."""
    games = history.loc[history["season"] == season, ["week", "team", "opponent"]].dropna()
    out: dict[int, dict[str, str]] = {}
    for week, team, opp in games.drop_duplicates().itertuples(index=False):
        out.setdefault(int(week), {})[str(team)] = str(opp)
    return out


def rest_of_season_backtest(history: pd.DataFrame, season: int) -> pd.DataFrame:
    """Projected vs actual rest-of-season points per remaining week, with a naive baseline.

    Actual totals count missed games as 0 (injuries are part of what the projection faces).
    """
    schedule = schedule_from_history(history, season)
    cur = history[history["season"] == season]
    frames = []
    for start in ROS_FROM_WEEKS:
        before = cur[cur["week"] < start]
        counts = before.groupby("gsis_id").size()
        eligible = counts[counts >= ROS_MIN_GAMES].index
        played = before[before["gsis_id"].isin(eligible)].sort_values("week")
        latest = played.groupby("gsis_id").last()  # the team he plays for now
        targets = latest.reset_index()[["gsis_id", "position", "team"]]
        weeks = tuple(range(start, ROS_LAST_WEEK + 1))  # regular season, every week equal
        horizon = Horizon(weeks, dict.fromkeys(weeks, 1.0), frozenset())
        proj = project_rest_of_season(history, targets, season, horizon, schedule)
        after = cur[(cur["week"] >= start) & (cur["week"] <= ROS_LAST_WEEK)]
        actual = after.groupby("gsis_id")["points"].sum()
        naive_avg = before.groupby("gsis_id")["points"].mean()
        n_weeks = len(horizon.weeks)
        df = pd.DataFrame(
            {
                "gsis_id": proj["gsis_id"],
                "position": proj["position"],
                "start": start,
                "proj": proj["ros_points"] / n_weeks,
                "actual": proj["gsis_id"].map(actual).fillna(0.0) / n_weeks,
                # naive: season-to-date average, for every remaining game the team plays
                "naive": proj["gsis_id"].map(naive_avg) * proj["games"] / n_weeks,
            }
        )
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def ros_section(ros: pd.DataFrame, season: int) -> list[str]:
    def mae(col: str, g: pd.DataFrame) -> float:
        return float((g[col] - g["actual"]).abs().mean())

    def rank(col: str, g: pd.DataFrame) -> float:
        corrs = [
            grp[col].rank().corr(grp["actual"].rank())  # Spearman, without SciPy
            for _, grp in g.groupby(["start", "position"])
            if len(grp) > 2
        ]
        return float(pd.Series(corrs).mean())

    lines = [
        f"## Rest of season ({season}, held out)",
        "",
        f"From weeks {', '.join(map(str, ROS_FROM_WEEKS))}: projected points per remaining week "
        f"through week {ROS_LAST_WEEK} vs actual (missed games count as 0), for players with "
        f"{ROS_MIN_GAMES}+ games so far. Naive: season-to-date average for each remaining game. "
        f"Overall MAE **{mae('proj', ros):.2f}** per week (naive {mae('naive', ros):.2f}), rank "
        f"correlation {rank('proj', ros):.3f} (naive {rank('naive', ros):.3f}).",
        "",
        "| Position | Players | MAE / week | Naive MAE | Rank corr | Naive rank corr |",
        "|---|---|---|---|---|---|",
    ]
    for pos, g in ros.groupby("position"):
        lines.append(
            f"| {pos} | {len(g):,} | {mae('proj', g):.2f} | {mae('naive', g):.2f} "
            f"| {rank('proj', g):.3f} | {rank('naive', g):.3f} |"
        )
    lines.append("")
    return lines


def with_ranges(df: pd.DataFrame, cal: Any) -> pd.DataFrame:
    rng = [apply_range(p, pos, cal) for p, pos in zip(df["proj"], df["position"], strict=True)]
    out = df.copy()
    out["p10"], out["p50"], out["p90"] = zip(*rng, strict=True)
    return out


def _table(rows: dict[str, dict[str, Any]], naive: dict[str, dict[str, Any]]) -> list[str]:
    header = "| Position | Games | MAE | Naive MAE | RMSE | Bias | Rank corr | 80% coverage |"
    lines = [header, "|---|---|---|---|---|---|---|---|"]
    for pos, g in rows.items():
        coverage = g.get("coverage_80", float("nan"))
        lines.append(
            f"| {pos} | {g['n']:,} | {g['mae']:.2f} | {naive[pos]['mae']:.2f} | {g['rmse']:.2f} "
            f"| {g['bias']:+.2f} | {g['rank_corr']:.3f} | {coverage:.1%} |"
        )
    return lines


def report(
    df_fit: pd.DataFrame,
    df_test: pd.DataFrame,
    fit_seasons: list[int],
    test: int,
    ros: pd.DataFrame | None = None,
) -> str:
    cal = fit_calibration(df_fit, MODEL_VERSION, f"{fit_seasons[0]}-{fit_seasons[-1]}")
    graded = with_ranges(df_test, cal)
    by_pos = metrics.grade_by_position(graded)
    naive = metrics.grade_by_position(graded.assign(proj=graded["naive"]))
    overall = metrics.grade(graded)
    overall_naive = metrics.grade(graded.assign(proj=graded["naive"]))
    lines = [
        "---",
        'title: "Backtest Report (projection model v1)"',
        f"date: {date.today().isoformat()}",
        "tags: [model, backtest, p1, p2]",
        "---",
        f"# Backtest Report: projection model {MODEL_VERSION}",
        "",
        "Generated by `python -m app.scripts.backtest --report ...`. Walk-forward: every week is "
        "projected using only earlier games. Scoring: Sleeper default half-PPR. Ranges were fit "
        f"on {fit_seasons[0]}-{fit_seasons[-1]} and are evaluated here on **{test}, held out**. "
        "Injury and depth-chart adjustments are not included (no historical data), so live "
        "accuracy on players listed Out/Questionable should be better than shown.",
        "",
        f"## Held-out season {test}",
        "",
        f"Overall MAE **{overall['mae']:.2f}** (naive season average: {overall_naive['mae']:.2f}), "
        f"rank correlation {overall['rank_corr']:.3f} (naive {overall_naive['rank_corr']:.3f}), "
        f"80% range coverage **{overall['coverage_80']:.1%}**.",
        "",
        *_table(by_pos, naive),
        "",
        "## Error by projected points (held out)",
        "",
        "| Projected | MAE |",
        "|---|---|",
        *[f"| {k} | {v:.2f} |" for k, v in overall["mae_by_bucket"].items()],
        "",
        *(ros_section(ros, test) if ros is not None else []),
        "## Definitions",
        "MAE: average absolute miss in points (headline). Naive: season-to-date average, or last "
        "season's if no games yet. Bias: average (projection - actual). Rank corr: Spearman "
        "correlation within each position-week (what start/sit depends on). Coverage: share of "
        "actual scores inside the 10th-90th percentile range (target ~ 80%). Definitions from "
        "[ADR-031](../Decisions/ADR-031-Approved-Reuses.md).",
        "",
        "Related: [Projection Model](../Specs/Projection-Model.md) · "
        "[P1 Build Plan](P1-Build-Plan.md) · [P2 Build Plan](P2-Build-Plan.md)",
    ]
    return "\n".join(lines) + "\n"


async def load(seasons: list[int]) -> pd.DataFrame:
    async with get_sessionmaker()() as db:
        rows = await load_stat_rows(db, seasons)
    await get_engine().dispose()
    if rows.empty:
        raise SystemExit("No nflverse rows in the database: run the ingest_nflverse job first.")
    return scored_history(rows, REFERENCE_RULES)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", type=int, default=2022, help="first season of history")
    parser.add_argument("--test", type=int, default=2025, help="held-out season")
    parser.add_argument("--write-calibration", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    history = asyncio.run(load(list(range(args.first, args.test + 1))))
    fit_seasons = list(range(args.first + 1, args.test))  # first season is history only
    df = walk_forward(history, [*fit_seasons, args.test])
    df_fit, df_test = df[df["season"].isin(fit_seasons)], df[df["season"] == args.test]

    ros = rest_of_season_backtest(history, args.test)
    text = report(df_fit, df_test, fit_seasons, args.test, ros)
    print(text)
    if args.report:
        args.report.write_text(text, encoding="utf-8")
    if args.write_calibration:
        # Production ranges use every backtested season, including the held-out one.
        seasons = f"{fit_seasons[0]}-{args.test} walk-forward, half-PPR"
        cal = fit_calibration(df, MODEL_VERSION, seasons)
        CALIBRATION_FILE.write_text(cal.to_json() + "\n", encoding="utf-8")
        print(f"wrote {CALIBRATION_FILE}")


if __name__ == "__main__":
    main()
