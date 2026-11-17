"""Compare two model versions on the same player-games: the keep rule used while building, and
ADR-061's ship rule over the four test seasons (`ship_evidence`, `ship_rule`).

Both frames hold one row per player-game with: gsis_id, position, season, week, actual, proj,
naive, and `injury_flag` (features/injury_games.py). They must cover the same rows; the
comparison is paired, so a model is never judged on easier players than its rival.

"Bigger than chance" is a paired bootstrap over weeks: weeks are resampled with replacement and
the change in average miss is recomputed 2,000 times. The change counts only if the whole 95%
interval is on the better side of zero.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.model import metrics
from app.model.features.injury_games import excluded

KEY = ["gsis_id", "season", "week"]
BOOTSTRAPS = 2000
SEED = 20261112
WORSE_LIMIT = 0.05  # no position may get worse by more than this many points (ADR-061)


@dataclass(frozen=True)
class Diff:
    n: int
    base_mae: float
    cand_mae: float
    change: float  # candidate - baseline: negative is better
    low: float
    high: float  # 95% interval of the change

    @property
    def better(self) -> bool:
        return self.high < 0

    @property
    def worse(self) -> bool:
        return self.low > 0


def pair(base: pd.DataFrame, cand: pd.DataFrame) -> pd.DataFrame:
    """One row per player-game with both models' projections side by side."""
    cols = [*KEY, "position", "actual", "naive", "injury_flag"]
    merged = base[[*cols, "proj"]].merge(
        cand[[*KEY, "proj"]], on=KEY, how="inner", suffixes=("_base", "_cand")
    )
    if len(merged) != len(base) or len(merged) != len(cand):
        raise ValueError("The two models must be graded on exactly the same player-games")
    merged["startable"] = metrics.startable_mask(merged, "naive")
    merged["weeks"] = metrics.week_group(merged)
    merged["left_out"] = excluded(merged["injury_flag"])
    return merged


def bootstrap(paired: pd.DataFrame) -> Diff:
    """Change in average absolute miss (candidate - baseline) with a paired week bootstrap."""
    if paired.empty:
        return Diff(0, float("nan"), float("nan"), float("nan"), float("nan"), float("nan"))
    err_b = (paired["proj_base"] - paired["actual"]).abs()
    err_c = (paired["proj_cand"] - paired["actual"]).abs()
    by_week = (
        pd.DataFrame(
            {
                "d": err_c - err_b,
                "b": err_b,
                "c": err_c,
                "season": paired["season"],
                "week": paired["week"],
            }
        )
        .groupby(["season", "week"])
        .agg(d=("d", "sum"), b=("b", "sum"), c=("c", "sum"), n=("d", "size"))
    )
    n_total = float(by_week["n"].sum())
    change = float(by_week["d"].sum() / n_total)
    rng = np.random.default_rng(SEED)
    picks = rng.integers(0, len(by_week), size=(BOOTSTRAPS, len(by_week)))
    d, n = by_week["d"].to_numpy(), by_week["n"].to_numpy()
    samples = d[picks].sum(axis=1) / n[picks].sum(axis=1)
    low, high = np.percentile(samples, [2.5, 97.5])
    return Diff(
        int(n_total),
        float(by_week["b"].sum() / n_total),
        float(by_week["c"].sum() / n_total),
        change,
        float(low),
        float(high),
    )


def slice_diff(
    paired: pd.DataFrame,
    *,
    startable: bool,
    weeks: str | None,
    position: str | None = None,
    include_injury_games: bool = False,
) -> Diff:
    """The change on one slice. Injury games are left out unless asked for."""
    mask = pd.Series(True, index=paired.index)
    if startable:
        mask &= paired["startable"]
    if weeks is not None:
        mask &= paired["weeks"] == weeks
    if position is not None:
        mask &= paired["position"] == position
    if not include_injury_games:
        mask &= ~paired["left_out"]
    return bootstrap(paired[mask])


@dataclass(frozen=True)
class Verdict:
    kept: bool
    positions_kept: tuple[str, ...]  # kept for these positions only when `kept` is False
    reasons: tuple[str, ...]


def verdict(tuning: pd.DataFrame, check: pd.DataFrame, weeks: str | None = "5+") -> Verdict:
    """The keep rule. `tuning` and `check` are `pair()` frames for the tuning and check seasons."""
    reasons: list[str] = []
    t = slice_diff(tuning, startable=True, weeks=weeks)
    c = slice_diff(check, startable=True, weeks=weeks)
    if not t.better:
        reasons.append(f"tuning seasons: change {t.change:+.3f}, not clearly better than chance")
    if not c.better:
        reasons.append(f"check season: change {c.change:+.3f}, not clearly better than chance")

    worse = []
    helped = []
    for pos in sorted(metrics.STARTABLE_TOP):
        tp = slice_diff(tuning, startable=True, weeks=weeks, position=pos)
        cp = slice_diff(check, startable=True, weeks=weeks, position=pos)
        if tp.change > WORSE_LIMIT or cp.change > WORSE_LIMIT:
            worse.append(pos)
        elif tp.better and cp.better:
            helped.append(pos)
    if worse:
        reasons.append(f"worse by more than {WORSE_LIMIT} points at {', '.join(worse)}")
    kept = not reasons
    return Verdict(kept, () if kept else tuple(helped), tuple(reasons))


# --------------------------------------------------------------------------- ship rule (ADR-061)
@dataclass(frozen=True)
class ShipEvidence:
    """Everything ADR-061's ship rule reads. Startable players (picked by season average), all
    weeks, injury games left out; change = candidate - live model, negative is better."""

    pooled: Diff  # the test seasons together, with the week bootstrap
    seasons: dict[int, Diff]  # each test season on its own
    positions: dict[str, Diff]  # each position, test seasons pooled
    final: Diff | None  # the current season's weeks so far: the one look before shipping


def ship_evidence(paired: pd.DataFrame, final: pd.DataFrame | None = None) -> ShipEvidence:
    """`paired`: a `pair()` frame over the test seasons; `final`: one over the current season's
    weeks, or None while it has not been looked at (it is looked at once, before shipping)."""

    def on(frame: pd.DataFrame, position: str | None = None) -> Diff:
        return slice_diff(frame, startable=True, weeks=None, position=position)

    present = set(paired["position"].unique())
    return ShipEvidence(
        on(paired),
        {int(s): on(paired[paired["season"] == s]) for s in sorted(paired["season"].unique())},
        {pos: on(paired, position=pos) for pos in sorted(metrics.STARTABLE_TOP) if pos in present},
        None if final is None else on(final),
    )


def ship_rule(e: ShipEvidence) -> Verdict:
    """ADR-061 decision 4: ship only if every condition holds; `reasons` lists each one that
    fails, in plain words, for the report."""
    reasons: list[str] = []
    if not e.pooled.better:
        reasons.append(f"test seasons pooled: change {e.pooled.change:+.3f}, "
                       "not better beyond chance")  # fmt: skip
    wins = sum(d.change < 0 for d in e.seasons.values())
    if wins < 3:
        reasons.append(f"better in only {wins} of {len(e.seasons)} test seasons (needs 3)")
    for pos, d in e.positions.items():
        if d.change > WORSE_LIMIT:
            reasons.append(f"{pos}: worse by {d.change:.3f} points (limit {WORSE_LIMIT})")
    # Until the one look at 2026 (step 11), the rule is read on the test seasons alone:
    # if e.final is None:
    #     reasons.append("2026 weeks not looked at yet (the one look comes in step 11)")
    if e.final is not None and e.final.worse:
        reasons.append(f"2026 weeks: change {e.final.change:+.3f}, worse beyond chance")
    return Verdict(not reasons, (), tuple(reasons))


def _flag(d: Diff) -> str:
    if d.n == 0:
        return "no games"
    return "better" if d.better else "worse" if d.worse else "noise"


def _row(label: str, d: Diff) -> str:
    return (
        f"| {label} | {d.n:,} | {d.base_mae:.3f} | {d.cand_mae:.3f} | {d.change:+.3f} "
        f"| {d.low:+.3f} to {d.high:+.3f} | {_flag(d)} |"
    )


def render(base: str, cand: str, tuning: pd.DataFrame, check: pd.DataFrame, title: str) -> str:
    """Markdown comparison of two model configs, plus the keep-rule verdict."""
    head = f"| Slice | Games | {base} miss | {cand} miss | Change | 95% interval | Result |"
    lines = [
        f"# {title}",
        "",
        f"Baseline `{base}` against candidate `{cand}`. Average miss in points; a negative "
        "change is better. Injury games are left out unless a row says otherwise.",
        "",
    ]
    for name, frame in (("Tuning seasons", tuning), ("Check season", check)):
        seasons = sorted(frame["season"].unique())
        left = int(frame["left_out"].sum())
        lines += [
            f"## {name} ({', '.join(map(str, seasons))})",
            "",
            f"{left:,} of {len(frame):,} player-games left out for injuries.",
            "",
            head,
            "|---|---|---|---|---|---|---|",
            _row("Startable, weeks 5+", slice_diff(frame, startable=True, weeks="5+")),
            _row("Startable, weeks 1-4", slice_diff(frame, startable=True, weeks="1-4")),
            _row("All players, weeks 5+", slice_diff(frame, startable=False, weeks="5+")),
            _row(
                "Startable, weeks 5+, injury games counted",
                slice_diff(frame, startable=True, weeks="5+", include_injury_games=True),
            ),
        ]
        for pos in sorted(metrics.STARTABLE_TOP):
            d = slice_diff(frame, startable=True, weeks="5+", position=pos)
            lines.append(_row(f"{pos}, startable, weeks 5+", d))
        lines.append("")
    v = verdict(tuning, check)
    lines += ["## Keep rule", ""]
    if v.kept:
        lines.append(
            "**Kept.** Better on the tuning seasons and the check season, beyond chance, "
            "and no position worse than 0.05."
        )
    else:
        lines.append("**Not kept.**")
        lines += [f"- {r}" for r in v.reasons]
        if v.positions_kept:
            lines.append(
                f"- Clearly better on both sets at: {', '.join(v.positions_kept)} "
                "(could be kept for those positions only)."
            )
    return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class SweepRow:
    name: str
    tuning: Diff
    check: Diff
    tuning_opener: Diff
    check_opener: Diff
    worst_position: tuple[str, float]  # the position that moved most the wrong way (either set)
    verdict: Verdict


def summarize(name: str, tuning: pd.DataFrame, check: pd.DataFrame) -> SweepRow:
    """One idea against the baseline: the headline slices and the keep-rule verdict."""
    worst = ("-", float("-inf"))
    for pos in sorted(metrics.STARTABLE_TOP):
        for frame in (tuning, check):
            d = slice_diff(frame, startable=True, weeks="5+", position=pos)
            if d.n and d.change > worst[1]:
                worst = (pos, d.change)
    return SweepRow(
        name,
        slice_diff(tuning, startable=True, weeks="5+"),
        slice_diff(check, startable=True, weeks="5+"),
        slice_diff(tuning, startable=True, weeks="1-4"),
        slice_diff(check, startable=True, weeks="1-4"),
        worst,
        verdict(tuning, check),
    )


def _cell(d: Diff) -> str:
    return f"{d.change:+.3f} ({d.low:+.3f} to {d.high:+.3f}) {_flag(d)}"


def render_sweep(baseline: str, rows: list[SweepRow], title: str) -> str:
    """One table for many ideas; startable players, weeks 5+ unless the column says otherwise."""
    lines = [
        f"# {title}",
        "",
        f"Each idea against `{baseline}`. Change in average miss (points, negative is better) "
        "with the 95% interval; startable players, injury games left out.",
        "",
        "| Idea | Tuning 5+ | Check 5+ | Tuning wk 1-4 | Check wk 1-4 | Worst position "
        "| Keep rule |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in sorted(rows, key=lambda r: r.tuning.change + r.check.change):
        verdict_text = (
            "**kept**"
            if r.verdict.kept
            else "for " + "/".join(r.verdict.positions_kept)
            if r.verdict.positions_kept
            else "no"
        )
        lines.append(
            f"| `{r.name}` | {_cell(r.tuning)} | {_cell(r.check)} | {_cell(r.tuning_opener)} "
            f"| {_cell(r.check_opener)} | {r.worst_position[0]} {r.worst_position[1]:+.3f} "
            f"| {verdict_text} |"
        )
    return "\n".join(lines) + "\n"
