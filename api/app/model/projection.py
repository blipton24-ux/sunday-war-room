"""Projection model v1 (docs/Specs/Projection-Model.md). Pure: DataFrames in, DataFrame out.

For one target week (season S, week W) and a set of players:

1. score history with the league's rules            (done by the caller via scoring.score)
2. baseline   recency-weighted mean of season-S games before W, blended with season S-1
3. opponent   how much this week's opponent allows to the position, clamped and faded early
4. role       recent snap share vs the player's season share (RB/WR/TE), clamped
5. injury     Out/IR -> 0, Doubtful/Questionable discounted; backup QBs heavily discounted
6. range      p10/p50/p90 from backtested residual quantiles (app/model/distribution.py)

Every step appends a factor {name, value, effect, note} so the UI can show "why this number".
**Only data from before week W is used** (walk-forward safe), which is what makes the
backtest honest and lets projections be frozen at kickoff.

P4 ideas (app/model/config.py) add optional steps between 2 and 5. With every switch off, as
in `SHIPPED`, the math is exactly the shipped model.

Bump MODEL_VERSION in the same commit as any change to the math (Integrity rules).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from app.model.config import SHIPPED, ModelConfig
from app.model.distribution import Calibration, apply_range
from app.model.features import defense as defense_features
from app.model.features import opportunity, rushing
from app.model.features.context import LEAGUE_POINTS, Extras, is_dome
from app.model.features.injury_games import excluded

MODEL_VERSION = "1.1.0"

HALF_LIFE_GAMES = 4.0  # a game 4 games ago counts half as much as the latest one
PRIOR_GAMES = 3.0  # last season's average counts like this many games of this season
PRIOR_QUANTILE = 0.30  # no-history players start at the 30th percentile of their position
OPP_CLAMP = 0.25  # opponent effect limited to +-25%
OPP_FADE_GAMES = 4.0  # ...and weighted n/(n+4): week 2 barely moves, week 10 mostly trusted
ROLE_CLAMP = 0.15
ROLE_POSITIONS = frozenset({"RB", "WR", "TE"})
SKILL = ("QB", "RB", "WR", "TE")
PASSING_GAME = frozenset({"QB", "WR", "TE"})
INJURY_MULTIPLIER = {
    "out": 0.0, "ir": 0.0, "pup": 0.0, "sus": 0.0, "na": 0.0, "cov": 0.0,
    "doubtful": 0.25, "questionable": 0.92,
}  # fmt: skip
BACKUP_QB_MULTIPLIER = 0.25
WIND_FREE_MPH = 12.0  # wind below this does not matter
ROOKIE_CLASSES = 3  # earlier draft classes behind a rookie starting value

HISTORY_COLUMNS = ("gsis_id", "season", "week", "position", "team", "opponent", "points", "snap")
TARGET_COLUMNS = ("gsis_id", "position", "team", "opponent")  # + optional injury/depth columns
# Raw stat columns the P4 ideas read (backtest only; live frames carry none of them).
RAW_COLUMNS = (
    "targets", "carries", "attempts", "receptions", "passing_yards", "passing_tds",
    "passing_interceptions", "rushing_yards", "rushing_tds", "receiving_yards", "receiving_tds",
    "def_sacks", "def_interceptions",
)  # fmt: skip


@dataclass(frozen=True)
class Context:
    season: int
    week: int


def _factor(name: str, value: float, effect: float, note: str) -> dict[str, Any]:
    return {"name": name, "value": round(value, 3), "effect": round(effect, 2), "note": note}


def _ewm(points: np.ndarray, half_life: float = HALF_LIFE_GAMES) -> float:
    n = len(points)
    weights = 0.5 ** ((n - 1 - np.arange(n)) / half_life)
    return float(np.dot(points, weights) / weights.sum())


def _opponent_table(
    cur: pd.DataFrame,
) -> tuple[dict[tuple[str, str], tuple[float, int]], dict[str, float]]:
    """(opponent, position) -> (avg points the position scored vs them per game, games)."""
    if cur.empty:
        return {}, {}
    per_game = cur.groupby(["opponent", "position", "season", "week"], as_index=False)[
        "points"
    ].sum()
    by_opp = per_game.groupby(["opponent", "position"])["points"].agg(["mean", "count"])
    league = by_opp.groupby(level="position")["mean"].mean().to_dict()
    table = {k: (float(r["mean"]), int(r["count"])) for k, r in by_opp.iterrows()}
    return table, {str(k): float(v) for k, v in league.items()}


def position_priors(last: pd.DataFrame, cur: pd.DataFrame) -> dict[str, float]:
    """Starting point for players with no history: a low-but-rosterable per-game value."""
    source = last if not last.empty else cur
    if source.empty:
        return {}
    per_player = source.groupby(["position", "gsis_id"])["points"].mean().reset_index()
    q = per_player.groupby("position")["points"].quantile(PRIOR_QUANTILE)
    return {str(k): float(v) for k, v in q.items()}


def _sack_int_ratios(cur: pd.DataFrame) -> dict[str, float]:
    """Per defense: how often it sacks and intercepts, relative to the league (1.0 = average)."""
    d = cur[cur["position"] == "DEF"]
    if d.empty:
        return {}
    per_team = d.groupby("team")[["def_sacks", "def_interceptions"]].mean()
    league = per_team.mean()
    rel = (per_team / league.where(league > 0)).mean(axis=1)
    return {str(t): float(v) for t, v in rel.items() if not np.isnan(v)}


def _rookie_table(
    history: pd.DataFrame, extras: Extras, season: int
) -> dict[tuple[str, int], float]:
    """(position, draft round bucket) -> a recent rookie's points per game. Earlier classes only."""
    key = ("rookie", season)
    if key in extras.cache:
        table: dict[tuple[str, int], float] = extras.cache[key]
        return table
    rows = history[
        (history["season"] < season)
        & (history["season"] >= season - ROOKIE_CLASSES)
        & history["position"].isin(SKILL)
    ]
    drafted = rows["gsis_id"].map(lambda g: extras.draft.get(str(g)))
    first = drafted.map(lambda d: d[0] if d else -1)
    bucket = drafted.map(lambda d: min(d[1], 4) if d else 0)
    rookies = rows[(first == rows["season"]) & (bucket > 0)].assign(bucket=bucket)
    means = rookies.groupby(["position", "bucket"])["points"].mean()
    buckets: list[Any] = means.index.tolist()
    table = {(str(p), int(b)): float(v) for (p, b), v in zip(buckets, means, strict=True)}
    extras.cache[key] = table
    return table


def _opportunity_fits(
    history: pd.DataFrame, season: int, extras: Extras | None
) -> dict[str, opportunity.OpportunityFit]:
    key = ("opportunity", season)
    if extras is not None and key in extras.cache:
        cached: dict[str, opportunity.OpportunityFit] = extras.cache[key]
        return cached
    fits = opportunity.fit_opportunity(history, season)
    if extras is not None:
        extras.cache[key] = fits
    return fits


DEFAULT_RECEIVING_SHARE = 0.3
CARRY_LIMITS = (0.7, 1.4)  # the carry-volume factor moves a projection by at most this much


def _cached[T](extras: Extras | None, key: tuple[str, int], build: Callable[[], T]) -> T:
    """A table fitted once per target season, kept on `extras` when there is one."""
    if extras is not None and key in extras.cache:
        cached: T = extras.cache[key]
        return cached
    value = build()
    if extras is not None:
        extras.cache[key] = value
    return value


def _split_baseline(
    games: pd.DataFrame | None,
    n: int,
    prior: float,
    has_last_season: bool,
    last_receiving: float | None,
    half_life: float,
    receiving_half_life: float,
    prior_games: float,
) -> tuple[float, str]:
    """E-34: rushing and receiving points averaged apart, each part with its own memory.
    With equal half-lives this is exactly the shipped baseline."""
    if games is not None and n:
        rec = (games["points"] * games["rec_share"].fillna(0.0)).to_numpy()
        rush = games["points"].to_numpy() - rec
        recent_rec, recent_rush = _ewm(rec, receiving_half_life), _ewm(rush, half_life)
        own_share = float(games["rec_share"].mean()) if games["rec_share"].notna().any() else 0.0
    else:
        recent_rec = recent_rush = 0.0
        own_share = 0.0
    if has_last_season and last_receiving is not None:
        prior_rec = min(last_receiving, prior)
    else:
        prior_rec = prior * own_share
    base_rec = _blend(recent_rec, n, prior_rec, prior_games)
    base_rush = _blend(recent_rush, n, prior - prior_rec, prior_games)
    return base_rush + base_rec, (
        f"; rushing {base_rush:.1f} and receiving {base_rec:.1f} averaged apart"
    )


def _carry_volume(
    config: ModelConfig,
    extras: Extras | None,
    target: dict[Any, Any],
    ctx: Context,
    games: pd.DataFrame,
    team_avg_carries: dict[str, float],
    fit: rushing.CarryFit | None,
    opp: Any,
) -> tuple[float, str] | None:
    """E-36: his recent share of team carries against his season share, times the carries his
    team is expected to get this week (from the spread) against its average. Applies to the
    rushing part of his points only."""
    shares = games["carry_share"].dropna().to_numpy()
    if len(shares) < 3 or shares.mean() <= 0:
        return None
    window = config.role_window
    trend = float(shares[-window:].mean() / shares.mean())
    team = str(target.get("team"))
    volume, volume_note = 1.0, ""
    game = extras.game(team, ctx.season, ctx.week) if extras is not None else None
    spread = game.get("spread") if game else None
    avg = team_avg_carries.get(team)
    if fit is not None and avg and spread is not None and not np.isnan(spread):
        volume = (avg + fit.per_point * float(spread)) / avg
        volume_note = f"; {team} expected {avg * volume:.0f} carries (average {avg:.0f})"
    rec_share = float(rushing.receiving_share(games).mean())  # NaN if he never produced
    rush_frac = 1.0 - (DEFAULT_RECEIVING_SHARE if np.isnan(rec_share) else rec_share)
    combined = (trend * volume) ** config.carry_volume
    mult = float(np.clip(1.0 + rush_frac * (combined - 1.0), *CARRY_LIMITS))
    return mult, (
        f"Share of team carries last {window} games {shares[-window:].mean():.0%} "
        f"vs season {shares.mean():.0%}{volume_note}"
    )


DEPTH_LIMITS = (0.6, 1.5)  # a depth-chart change moves a projection by at most this much
TEAMMATE_RECENT_WEEKS = 2  # a teammate counts as newly out if he played in this many weeks
TIER_NAMES = {1: "starter", 2: "next in line", 3: "deeper on the chart"}


def _depth_table(
    history: pd.DataFrame, season: int, extras: Extras | None
) -> dict[tuple[str, int], float]:
    """(position, depth tier) -> average points per game, from seasons before `season` only."""
    key = ("depth", season)
    if extras is not None and key in extras.cache:
        cached: dict[tuple[str, int], float] = extras.cache[key]
        return cached
    earlier = history[(history["season"] < season) & history["depth_tier"].notna()]
    means = earlier.groupby(["position", "depth_tier"])["points"].mean()
    keys: list[Any] = means.index.tolist()
    table = {(str(p), int(t)): float(v) for (p, t), v in zip(keys, means, strict=True)}
    if extras is not None:
        extras.cache[key] = table
    return table


def _teammates(cur: pd.DataFrame) -> dict[tuple[str, str], list[tuple[str, float, int]]]:
    """(team, position) -> (player, points per game, last week played) for players with 2+
    games for that team this season (before the projected week)."""
    if cur.empty:
        return {}
    g = cur.groupby(["team", "position", "gsis_id"])
    stats = g["points"].agg(["mean", "count"]).join(g["week"].max().rename("last"))
    stats = stats[stats["count"] >= 2]
    out: dict[tuple[str, str], list[tuple[str, float, int]]] = {}
    keys: list[Any] = stats.index.tolist()
    for (team, pos, gid), mean, last in zip(keys, stats["mean"], stats["last"], strict=True):
        out.setdefault((str(team), str(pos)), []).append((str(gid), float(mean), int(last)))
    return out


def _availability(
    config: ModelConfig,
    extras: Extras | None,
    target: dict[Any, Any],
    gid: str,
    pos: str,
    ctx: Context,
    games: pd.DataFrame | None,
    depth_table: dict[tuple[str, int], float],
    last_tier: dict[str, float],
    mates: dict[tuple[str, str], list[tuple[str, float, int]]],
) -> list[tuple[str, float, str]]:
    """Round 2 ideas (ADR-058): a depth-chart change this week (E-14), a better teammate at his
    position newly out (E-15), the first game back from a reserve-list stay (E-20)."""
    steps: list[tuple[str, float, str]] = []
    if config.depth_rank and depth_table and pos in ROLE_POSITIONS:
        now = target.get("depth_tier")
        seen = games["depth_tier"].dropna() if games is not None else pd.Series(dtype=float)
        usual = float(seen.median()) if len(seen) else last_tier.get(str(gid))
        if now is not None and not pd.isna(now) and usual is not None and not np.isnan(usual):
            now_t, usual_t = int(now), round(usual)
            typical_now = depth_table.get((pos, now_t))
            typical_usual = depth_table.get((pos, usual_t))
            if now_t != usual_t and typical_now and typical_usual:
                ratio = typical_now / typical_usual
                mult = float(np.clip(1.0 + config.depth_rank * (ratio - 1.0), *DEPTH_LIMITS))
                note = f"{TIER_NAMES[now_t].capitalize()} this week, usually {TIER_NAMES[usual_t]}"
                steps.append(("depth chart", mult, note))
    if extras is None:
        return steps
    if config.teammate_out and pos in ROLE_POSITIONS:
        own = float(games["points"].mean()) if games is not None and len(games) else 0.0
        out = [
            m
            for m, avg, last in mates.get((str(target.get("team")), pos), [])
            if m != str(gid)
            and avg > own
            and last >= ctx.week - TEAMMATE_RECENT_WEEKS
            and (m, ctx.season, ctx.week) in extras.unavailable
        ]
        if out:
            note = f"A {pos} teammate who outscores him is out this week"
            steps.append(("teammate out", 1.0 + config.teammate_out, note))
    if config.return_discount:
        last_game = int(games["week"].max()) if games is not None and len(games) else 0
        away = [
            w for w in range(last_game + 1, ctx.week) if (str(gid), ctx.season, w) in extras.reserve
        ]
        if away:
            note = f"Back from a reserve list (weeks {away[0]}-{away[-1]})"
            steps.append(("first game back", 1.0 - config.return_discount, note))
    return steps


def _blend(recent: float, n: int, prior: float, prior_games: float) -> float:
    return (n * recent + prior_games * prior) / (n + prior_games)


def project_week(
    history: pd.DataFrame,
    targets: pd.DataFrame,
    ctx: Context,
    calibration: Calibration | None,
    config: ModelConfig = SHIPPED,
    extras: Extras | None = None,
) -> pd.DataFrame:
    """Project every row of `targets` (see `_project`). When the config has per-position
    settings, each group of positions that shares settings is projected on its own and the rows
    are returned in the order they came in."""
    if not config.overrides or targets.empty:
        return _project(history, targets, ctx, calibration, config.for_position(""), extras)
    groups: dict[ModelConfig, list[str]] = {}
    for pos in targets["position"].unique():
        groups.setdefault(config.for_position(str(pos)), []).append(pos)
    numbered = targets.assign(_row=range(len(targets)))
    parts = [
        _project(history, numbered[numbered["position"].isin(ps)], ctx, calibration, cfg, extras)
        for cfg, ps in groups.items()
    ]
    out = pd.concat(parts, ignore_index=True).sort_values("_row")
    return out.drop(columns=["_row"]).reset_index(drop=True)


def _project(
    history: pd.DataFrame,
    targets: pd.DataFrame,
    ctx: Context,
    calibration: Calibration | None,
    config: ModelConfig = SHIPPED,
    extras: Extras | None = None,
) -> pd.DataFrame:
    """Project every row of `targets` for ctx.season / ctx.week.

    history: one row per player-game with HISTORY_COLUMNS, points already scored with the
             league's rules. Rows at or after the target week are ignored (no leakage).
    targets: TARGET_COLUMNS; `opponent` None means no game (bye). Optional columns:
             `injury_status`, `depth_chart_order`.
    config:  switches for ideas under test (app/model/config.py); live code uses SHIPPED.
    extras:  game context for ideas that need it (betting lines, draft capital); None if unused.
    Returns targets + points, p10, p50, p90, factors.
    """
    hist = history[
        (history["season"] < ctx.season)
        | ((history["season"] == ctx.season) & (history["week"] < ctx.week))
    ]
    if config.needs_raw_stats and not set(RAW_COLUMNS) <= set(history.columns):
        # A history of points only (tests, older callers): the raw-stat ideas cannot run.
        config = config.without_raw_stats()
    if config.skip_injury_games_in_history and "injury_game" in hist.columns:
        hist = hist[~excluded(hist["injury_game"])]
    raw_cur = hist[hist["season"] == ctx.season]  # actual points, for the opponent tables
    opp_table, opp_league = _opponent_table(raw_cur)

    # -- P4 opportunity features: expected points, touchdown regression, usage share ------------
    fits: dict[str, opportunity.OpportunityFit] = {}
    if config.xfp_weight or config.td_regression:
        fits = _opportunity_fits(history, ctx.season, extras)
        if config.td_regression:
            hist = hist.assign(
                points=opportunity.regress_touchdowns(hist, fits, config.td_regression)
            )
        if config.xfp_weight:
            hist = hist.assign(xfp=opportunity.expected_points(hist, fits))
    if config.ypc_regression:  # E-35: rushing yards at the league's typical yards per carry
        ypc = _cached(extras, ("ypc", ctx.season), lambda: rushing.fit_ypc(history, ctx.season))
        hist = hist.assign(points=rushing.regress_ypc(hist, ypc, config.ypc_regression))
    if config.receiving_half_life is not None:  # E-34
        hist = hist.assign(rec_share=rushing.receiving_share(hist))
    if config.carry_volume:  # E-36
        hist = hist.assign(
            carry_share=hist["carries"] / rushing.team_carries(hist).where(lambda c: c > 0)
        )
    if config.nfl_xfp_weight:  # E-04; a game nflverse has no row for counts at face value
        nflverse_xfp = hist["xfp_nflverse"] if "xfp_nflverse" in hist.columns else np.nan
        hist = hist.assign(nxfp=pd.Series(nflverse_xfp, index=hist.index).fillna(hist["points"]))
    if config.usage_trend:
        hist = hist.assign(share=opportunity.usage_share(hist))

    cur = hist[hist["season"] == ctx.season]
    last = hist[hist["season"] == ctx.season - 1]
    priors = position_priors(last, cur)

    allowed = None
    if config.def_pass or config.def_run or config.def_schedule_adjust:
        allowed = defense_features.build_allowed(raw_cur, SKILL)
    sack_int = _sack_int_ratios(raw_cur) if config.def_sack_int else {}
    rookie_table = (
        _rookie_table(history, extras, ctx.season) if config.rookie_prior and extras else {}
    )

    cur_by = {k: g.sort_values("week") for k, g in cur.groupby("gsis_id")}
    raw_by = {k: g for k, g in raw_cur.groupby("gsis_id")} if allowed is not None else {}
    last_mean = last.groupby("gsis_id")["points"].agg(["mean", "count"])
    last_by = {k: (float(r["mean"]), int(r["count"])) for k, r in last_mean.iterrows()}
    last_xfp: dict[str, float] = {}
    if config.xfp_weight:
        last_xfp = {str(k): float(v) for k, v in last.groupby("gsis_id")["xfp"].mean().items()}
    last_nxfp: dict[str, float] = {}
    if config.nfl_xfp_weight:
        last_nxfp = {str(k): float(v) for k, v in last.groupby("gsis_id")["nxfp"].mean().items()}
    depth_table: dict[tuple[str, int], float] = {}
    last_tier: dict[str, float] = {}
    if config.depth_rank and "depth_tier" in hist.columns:
        depth_table = _depth_table(history, ctx.season, extras)
        last_tier = {
            str(k): float(v) for k, v in last.groupby("gsis_id")["depth_tier"].median().items()
        }
    mates = _teammates(raw_cur) if config.teammate_out and extras is not None else {}
    last_split: dict[str, float] = {}
    if config.receiving_half_life is not None:
        last_split = {
            str(k): float(v)
            for k, v in last.assign(rec_pts=last["points"] * last["rec_share"].fillna(0.0))
            .groupby("gsis_id")["rec_pts"]
            .mean()
            .items()
        }
    team_avg_carries: dict[str, float] = {}
    carry_fit: rushing.CarryFit | None = None
    if config.carry_volume:
        per_team_game = raw_cur.groupby(["team", "week"])["carries"].sum()
        keys: list[Any] = per_team_game.index.tolist()
        totals: dict[str, list[float]] = {}
        for (team, _week), carries in zip(keys, per_team_game, strict=True):
            totals.setdefault(str(team), []).append(float(carries))
        team_avg_carries = {t: float(np.mean(v)) for t, v in totals.items()}
        if extras is not None:
            carry_fit = _cached(
                extras,
                ("carries", ctx.season),
                lambda: rushing.fit_carries_vs_spread(history, extras.games, ctx.season),
            )
    league_implied = (
        extras.league_implied.get((ctx.season, ctx.week), LEAGUE_POINTS) if extras else 0.0
    )

    out_rows = []
    for t in targets.to_dict("records"):
        gid, pos, opp = t["gsis_id"], t["position"], t.get("opponent")
        factors: list[dict[str, Any]] = []
        half_life = config.half_life_for(pos)
        prior_games = config.prior_games_for(pos, ctx.week)

        # -- 2. baseline ----------------------------------------------------------
        games = cur_by.get(gid)
        n = 0 if games is None else len(games)
        prev = last_by.get(gid)
        if n == 0 and prev is None:
            base = float(priors.get(pos, 0.0))
            note = f"No NFL history yet: starts at a typical low-end {pos} value"
            drafted = extras.draft.get(str(gid)) if extras and rookie_table else None
            if drafted and drafted[0] == ctx.season:
                bucket = min(drafted[1], 4)
                if (pos, bucket) in rookie_table:
                    base = rookie_table[(pos, bucket)]
                    note = (
                        f"Rookie drafted in round {drafted[1]}: "
                        f"starts at what recent {pos}s like him scored"
                    )
        else:
            recent = _ewm(games["points"].to_numpy(), half_life) if games is not None else 0.0
            prior = prev[0] if prev else float(priors.get(pos, recent))
            base = _blend(recent, n, prior, prior_games)
            split_note = ""
            if config.receiving_half_life is not None and pos in ROLE_POSITIONS:
                base, split_note = _split_baseline(
                    games, n, prior, prev is not None, last_split.get(str(gid)), half_life,
                    config.receiving_half_life, prior_games,
                )  # fmt: skip
            parts = []
            if n:
                parts.append(f"{n} game{'s' * (n != 1)} this season (recent-weighted {recent:.1f})")
            parts.append(
                f"{ctx.season - 1} average {prev[0]:.1f} over {prev[1]} games"
                if prev
                else f"typical {pos} value {prior:.1f} (no {ctx.season - 1} games)"
            )
            note = "Blend of " + " and ".join(parts) + split_note
            if config.xfp_weight and pos in fits and (n or gid in last_xfp):
                xs = games["xfp"].to_numpy() if games is not None else np.array([])
                recent_x = _ewm(xs, half_life) if n else 0.0
                prior_x = last_xfp.get(gid, float(priors.get(pos, recent_x)))
                base_x = _blend(recent_x, n, prior_x, prior_games)
                base = (1 - config.xfp_weight) * base + config.xfp_weight * base_x
                note += f"; {config.xfp_weight:.0%} from volume (expected points {base_x:.1f})"
            if config.nfl_xfp_weight and pos in SKILL and (n or gid in last_nxfp):
                xs = games["nxfp"].to_numpy() if games is not None else np.array([])
                recent_x = _ewm(xs, half_life) if n else 0.0
                prior_x = last_nxfp.get(gid, float(priors.get(pos, recent_x)))
                base_n = _blend(recent_x, n, prior_x, prior_games)
                base = (1 - config.nfl_xfp_weight) * base + config.nfl_xfp_weight * base_n
                note += f"; {config.nfl_xfp_weight:.0%} from nflverse expected points {base_n:.1f}"
        pts = base
        factors.append(_factor("baseline", base, base, note))

        # -- bye ------------------------------------------------------------------
        if opp is None or (isinstance(opp, float) and np.isnan(opp)):
            factors.append(_factor("bye", 0.0, -pts, "No game this week"))
            out_rows.append({**t, "raw_points": 0.0, "factors": factors})
            continue

        # -- 3. opponent ----------------------------------------------------------
        mult, note = _opponent(
            config, pos, opp, ctx, opp_table, opp_league, allowed, raw_by.get(gid)
        )
        factors.append(_factor("opponent", mult, pts * (mult - 1), note))
        pts *= mult

        if config.def_sack_int and pos == "QB" and opp in sack_int:
            ratio = sack_int[opp]
            mult = 1.0 - float(np.clip(config.def_sack_int * (ratio - 1.0), -0.1, 0.1))
            factors.append(
                _factor(
                    "pressure",
                    mult,
                    pts * (mult - 1),
                    f"{opp} sacks and intercepts at {ratio:.2f}x the league rate",
                )
            )
            pts *= mult

        # -- 4. role --------------------------------------------------------------
        role = _role(config, pos, games, n)
        if role is not None:
            mult, note = role
            factors.append(_factor("role", mult, pts * (mult - 1), note))
            pts *= mult

        if config.carry_volume and pos in ROLE_POSITIONS and games is not None and n >= 3:
            step = _carry_volume(config, extras, t, ctx, games, team_avg_carries, carry_fit, opp)
            if step is not None:
                mult, note = step
                factors.append(_factor("carry volume", mult, pts * (mult - 1), note))
                pts *= mult

        # -- P4 round 2: depth chart, teammates out, first game back -----------------
        for name, mult, note in _availability(
            config, extras, t, gid, pos, ctx, games, depth_table, last_tier, mates
        ):
            factors.append(_factor(name, mult, pts * (mult - 1), note))
            pts *= mult

        # -- P4 game context: betting lines, weather, rest ---------------------------
        if extras is not None and config.needs_extras:
            for name, mult, note in _context(config, extras, t, opp, pos, ctx, league_implied):
                factors.append(_factor(name, mult, pts * (mult - 1), note))
                pts *= mult

        # -- 5. depth + injury (live data only; not in the backtest) ---------------
        depth = t.get("depth_chart_order")
        if pos == "QB" and depth is not None and not pd.isna(depth) and int(depth) >= 2:
            mult = BACKUP_QB_MULTIPLIER
            factors.append(
                _factor("depth", mult, pts * (mult - 1), f"QB{int(depth)} on depth chart")
            )
            pts *= mult
        status = str(t.get("injury_status") or "").strip()
        if status:
            mult = INJURY_MULTIPLIER.get(status.lower(), 1.0)
            if mult != 1.0:
                factors.append(_factor("injury", mult, pts * (mult - 1), f"Listed {status}"))
                pts *= mult

        out_rows.append(
            {**t, "raw_points": max(pts, 0.0) if pos != "DEF" else pts, "factors": factors}
        )

    out = pd.DataFrame(out_rows)
    if out.empty:
        return out.assign(points=[], p10=[], p50=[], p90=[])
    out["points"] = out["raw_points"].round(2)
    if calibration is not None:
        ranges = [
            apply_range(p, pos, calibration)
            for p, pos in zip(out["raw_points"], out["position"], strict=True)
        ]
        out["p10"], out["p50"], out["p90"] = zip(*ranges, strict=True)
    return out.drop(columns=["raw_points"])


def _opponent(
    config: ModelConfig,
    pos: str,
    opp: str,
    ctx: Context,
    opp_table: dict[tuple[str, str], tuple[float, int]],
    opp_league: dict[str, float],
    allowed: defense_features.Allowed | None,
    player_games: pd.DataFrame | None,
) -> tuple[float, str]:
    """The opponent factor: shipped (points allowed to the position) or the P4 split by part
    of the game and by who the defense has faced (E-06, E-07, E-09), with the E-10 limits."""
    clamp, fade = config.opp_clamp, config.opp_fade_games
    key = (opp, pos)
    if allowed is not None and pos in SKILL:
        games = allowed.games.get(key, 0)
        r_all = defense_features.ratio(allowed.total, allowed.league_total, key)
        if config.def_schedule_adjust and key in allowed.resid and allowed.scale.get(pos, 0) > 0:
            r_all = 1.0 + allowed.resid[key] / allowed.scale[pos]
        r_pass = (
            defense_features.ratio(allowed.passing, allowed.league_passing, key)
            if config.def_pass
            else r_all
        )
        r_run = (
            defense_features.ratio(allowed.running, allowed.league_running, key)
            if config.def_run
            else r_all
        )
        if r_all is None or r_pass is None or r_run is None or games == 0:
            return 1.0, f"Not enough {ctx.season} games to rate {opp} yet"
        share = defense_features.pass_share(player_games, pos)
        ratio = share * r_pass + (1.0 - share) * r_run
        weight = games / (games + fade)
        mult = 1.0 + float(np.clip(ratio - 1.0, -clamp, clamp)) * weight
        direction = "more" if ratio >= 1 else "less"
        return mult, (
            f"{opp} has allowed {abs(ratio - 1):.0%} {direction} than average to {pos}s "
            f"(passing game {share:.0%} of his points; {games} games; trusted {weight:.0%})"
        )
    allowed_pts = opp_table.get(key)
    avg = opp_league.get(pos)
    if allowed_pts and avg and avg > 0:
        ratio = allowed_pts[0] / avg
        weight = allowed_pts[1] / (allowed_pts[1] + fade)
        mult = 1.0 + float(np.clip(ratio - 1.0, -clamp, clamp)) * weight
        direction = "more" if ratio >= 1 else "less"
        return mult, (
            f"{opp} has allowed {abs(ratio - 1):.0%} {direction} than average to {pos}s "
            f"({allowed_pts[1]} games; trusted {weight:.0%} this early)"
        )
    return 1.0, f"Not enough {ctx.season} games to rate {opp} yet"


def _role(
    config: ModelConfig, pos: str, games: pd.DataFrame | None, n: int
) -> tuple[float, str] | None:
    """Recent usage against his own season norm (RB/WR/TE): snap share (shipped) or, with the
    usage-trend idea (E-05), his share of the team's targets and carries."""
    if pos not in ROLE_POSITIONS or games is None or n < 3:
        return None
    window = config.role_window
    if config.usage_trend:
        shares = games["share"].dropna().to_numpy()
        if len(shares) >= 3 and shares.mean() > 0:
            ratio = shares[-window:].mean() / shares.mean()
            mult = 1.0 + float(np.clip(ratio - 1.0, -config.role_clamp, config.role_clamp))
            return mult, (
                f"Share of team targets and carries last {window} games "
                f"{shares[-window:].mean():.0%} vs season {shares.mean():.0%}"
            )
        return None
    snaps = games["snap"].dropna().to_numpy()
    if len(snaps) >= 3 and snaps.mean() > 0:
        ratio = snaps[-window:].mean() / snaps.mean()
        mult = 1.0 + float(np.clip(ratio - 1.0, -config.role_clamp, config.role_clamp))
        return mult, (
            f"Snap share last {window} games {snaps[-window:].mean():.0%} "
            f"vs season {snaps.mean():.0%}"
        )
    return None


def _context(
    config: ModelConfig,
    extras: Extras,
    target: dict[Any, Any],
    opp: str,
    pos: str,
    ctx: Context,
    league_implied: float,
) -> list[tuple[str, float, str]]:
    """Betting-market, team-strength, venue and rest effects (E-11, E-12, E-13, E-21..E-25)."""
    team = target.get("team")
    game = extras.game(team, ctx.season, ctx.week)
    if game is None:
        return []
    steps: list[tuple[str, float, str]] = []
    implied = game.get("implied")
    spread = game.get("spread")

    if config.team_offense and pos in SKILL:
        s = extras.strength.get((str(team), ctx.season, ctx.week))
        if s is not None:
            steps.append(
                ("team offense", 1.0 + config.team_offense * (s - 1.0),
                 f"{team} scores at {s:.2f}x the league average")
            )  # fmt: skip
    if config.implied_total and pos in SKILL and implied is not None and not np.isnan(implied):
        ratio = float(implied) / league_implied
        steps.append(
            ("implied total", 1.0 + config.implied_total * (ratio - 1.0),
             f"Betting market expects {team} to score {implied:.1f} (average {league_implied:.1f})")
        )  # fmt: skip
    if config.game_script and pos in SKILL and spread is not None and not np.isnan(spread):
        lean = config.game_script * float(spread)  # a favourite runs more, an underdog passes
        factor = 1.0 + float(np.clip(lean if pos == "RB" else -0.5 * lean, -0.15, 0.15))
        steps.append(
            (
                "game script",
                factor,
                f"{team} is {'favoured' if spread > 0 else 'an underdog'} by {abs(spread):.1f}",
            )
        )
    if config.home_boost and pos in (*SKILL, "K"):
        home = bool(game.get("home"))
        steps.append(
            ("venue", 1.0 + (config.home_boost if home else -config.home_boost),
             "Home game" if home else "Road game")
        )  # fmt: skip
    wind = game.get("wind")
    if (
        config.wind_penalty
        and (pos in PASSING_GAME or pos == "K")
        and wind is not None
        and not np.isnan(wind)
        and not is_dome(game.get("roof"))
        and wind > WIND_FREE_MPH
    ):
        factor = max(0.85, 1.0 - config.wind_penalty * (float(wind) - WIND_FREE_MPH) / 5.0)
        steps.append(("weather", factor, f"Wind {wind:.0f} mph"))
    rest = game.get("rest")
    if config.rest_effect and pos in (*SKILL, "K") and rest is not None and not np.isnan(rest):
        if rest <= 5:
            steps.append(("rest", 1.0 - config.rest_effect, f"Short week ({rest:.0f} days)"))
        elif rest >= 10:
            steps.append(("rest", 1.0 + config.rest_effect, f"Extra rest ({rest:.0f} days)"))
    if config.kicker_model and pos == "K" and implied is not None and not np.isnan(implied):
        ratio = float(implied) / league_implied
        steps.append(
            ("team scoring", ratio**config.kicker_model, f"{team} implied score {implied:.1f}")
        )
    if config.defense_model and pos == "DEF":
        theirs = extras.game(opp, ctx.season, ctx.week)
        opp_implied = theirs.get("implied") if theirs else None
        if opp_implied is not None and not np.isnan(opp_implied) and opp_implied > 0:
            ratio = league_implied / float(opp_implied)
            steps.append(
                ("opposing offense", ratio**config.defense_model,
                 f"{opp} implied score {opp_implied:.1f}")
            )  # fmt: skip
    return steps
