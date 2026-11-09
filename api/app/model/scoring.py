"""Fantasy points from raw stats with a league's OWN rules (Projection Model step 1).

Never trusts a generic "PPR points" column. Each Sleeper rule maps to one of three shapes
(ADR-031):

* per-unit    points x quantity            ("rec_yd": 0.1 per receiving yard)
* tier        points if quantity >= N      ("bonus_rec_yd_100": 3 if 100+ yards)
* range-count points if lo <= quantity <= hi ("pts_allow_14_20": 1 if 14-20 allowed)

Rules with value 0 are ignored. Non-zero rules we can't compute are *reported* by
`check_rules`, never silently dropped. Pure functions: pandas/numpy in, numbers out.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

Shape = Literal["per_unit", "tier", "range"]
OFFENSE = frozenset({"QB", "RB", "WR", "TE"})
KICKER = frozenset({"K"})
DEFENSE = frozenset({"DEF"})
EVERYONE = OFFENSE | KICKER | DEFENSE


def col(name: str) -> Callable[[pd.DataFrame], pd.Series]:
    return lambda df: df.get(name, pd.Series(0.0, index=df.index)).fillna(0.0)


def total(*names: str) -> Callable[[pd.DataFrame], pd.Series]:
    def f(df: pd.DataFrame) -> pd.Series:
        out = pd.Series(0.0, index=df.index)
        for n in names:
            out = out + col(n)(df)
        return out

    return f


@dataclass(frozen=True)
class Rule:
    shape: Shape
    quantity: Callable[[pd.DataFrame], pd.Series]
    positions: frozenset[str]
    lo: float = 0.0  # tier threshold, or range lower bound
    hi: float = float("inf")  # range upper bound (inclusive)
    only_position: str | None = None  # e.g. TE-premium bonus applies to TEs only


def per_unit(q: Callable[[pd.DataFrame], pd.Series], pos: frozenset[str] = OFFENSE) -> Rule:
    return Rule("per_unit", q, pos)


def tier(q: Callable[[pd.DataFrame], pd.Series], at: float) -> Rule:
    return Rule("tier", q, OFFENSE, lo=at)


def pts_allowed(lo: float, hi: float = float("inf")) -> Rule:
    return Rule("range", col("points_allowed"), DEFENSE, lo=lo, hi=hi)


SLEEPER_RULES: dict[str, Rule] = {
    # passing
    "pass_yd": per_unit(col("passing_yards")),
    "pass_td": per_unit(col("passing_tds")),
    "pass_int": per_unit(col("passing_interceptions")),
    "pass_2pt": per_unit(col("passing_2pt_conversions")),
    "pass_cmp": per_unit(col("completions")),
    "pass_att": per_unit(col("attempts")),
    "pass_inc": per_unit(lambda df: col("attempts")(df) - col("completions")(df)),
    "pass_sack": per_unit(col("sacks_suffered")),
    "pass_fd": per_unit(col("passing_first_downs")),
    # rushing
    "rush_yd": per_unit(col("rushing_yards")),
    "rush_td": per_unit(col("rushing_tds")),
    "rush_2pt": per_unit(col("rushing_2pt_conversions")),
    "rush_att": per_unit(col("carries")),
    "rush_fd": per_unit(col("rushing_first_downs")),
    # receiving
    "rec": per_unit(col("receptions")),
    "rec_yd": per_unit(col("receiving_yards")),
    "rec_td": per_unit(col("receiving_tds")),
    "rec_2pt": per_unit(col("receiving_2pt_conversions")),
    "rec_tgt": per_unit(col("targets")),
    "rec_fd": per_unit(col("receiving_first_downs")),
    "bonus_rec_te": Rule("per_unit", col("receptions"), OFFENSE, only_position="TE"),
    "bonus_rec_rb": Rule("per_unit", col("receptions"), OFFENSE, only_position="RB"),
    "bonus_rec_wr": Rule("per_unit", col("receptions"), OFFENSE, only_position="WR"),
    # ball security, returns
    "fum": per_unit(col("fumbles_total")),
    "fum_lost": per_unit(
        total("rushing_fumbles_lost", "receiving_fumbles_lost", "sack_fumbles_lost")
    ),
    "fum_rec_td": per_unit(col("fumble_recovery_tds")),
    "st_td": Rule("per_unit", col("special_teams_tds"), OFFENSE | DEFENSE),
    "kr_yd": per_unit(col("kickoff_return_yards")),
    "pr_yd": per_unit(col("punt_return_yards")),
    # tier bonuses
    "bonus_pass_yd_300": tier(col("passing_yards"), 300),
    "bonus_pass_yd_400": tier(col("passing_yards"), 400),
    "bonus_rush_yd_100": tier(col("rushing_yards"), 100),
    "bonus_rush_yd_200": tier(col("rushing_yards"), 200),
    "bonus_rec_yd_100": tier(col("receiving_yards"), 100),
    "bonus_rec_yd_200": tier(col("receiving_yards"), 200),
    "bonus_rush_rec_yd_100": tier(total("rushing_yards", "receiving_yards"), 100),
    "bonus_rush_rec_yd_200": tier(total("rushing_yards", "receiving_yards"), 200),
    "bonus_pass_cmp_25": tier(col("completions"), 25),
    "bonus_rush_att_20": tier(col("carries"), 20),
    # kicking (nflverse already buckets FGs by distance: count columns)
    "fgm": per_unit(col("fg_made"), KICKER),
    "fga": per_unit(col("fg_att"), KICKER),
    "fgmiss": per_unit(col("fg_missed"), KICKER),
    "fgm_0_19": per_unit(col("fg_made_0_19"), KICKER),
    "fgm_20_29": per_unit(col("fg_made_20_29"), KICKER),
    "fgm_30_39": per_unit(col("fg_made_30_39"), KICKER),
    "fgm_40_49": per_unit(col("fg_made_40_49"), KICKER),
    "fgm_50_59": per_unit(col("fg_made_50_59"), KICKER),
    "fgm_60p": per_unit(col("fg_made_60_"), KICKER),
    "fgm_50p": per_unit(total("fg_made_50_59", "fg_made_60_"), KICKER),
    "fgmiss_0_19": per_unit(col("fg_missed_0_19"), KICKER),
    "fgmiss_20_29": per_unit(col("fg_missed_20_29"), KICKER),
    "fgmiss_30_39": per_unit(col("fg_missed_30_39"), KICKER),
    "fgmiss_40_49": per_unit(col("fg_missed_40_49"), KICKER),
    "fgmiss_50p": per_unit(total("fg_missed_50_59", "fg_missed_60_"), KICKER),
    "xpm": per_unit(col("pat_made"), KICKER),
    "xpa": per_unit(col("pat_att"), KICKER),
    "xpmiss": per_unit(col("pat_missed"), KICKER),
    # team defense
    "sack": per_unit(col("def_sacks"), DEFENSE),
    "int": per_unit(col("def_interceptions"), DEFENSE),
    "fum_rec": per_unit(col("fumble_recovery_opp"), DEFENSE),
    "ff": per_unit(col("def_fumbles_forced"), DEFENSE),
    "def_td": per_unit(col("def_tds"), DEFENSE),
    "safe": per_unit(col("def_safeties"), DEFENSE),
    "blk_kick": per_unit(total("def_fg_blocks", "def_punt_blocks", "def_pat_blocks"), DEFENSE),
    "def_st_td": per_unit(col("special_teams_tds"), DEFENSE),
    "pts_allow": per_unit(col("points_allowed"), DEFENSE),
    "pts_allow_0": pts_allowed(0, 0),
    "pts_allow_1_6": pts_allowed(1, 6),
    "pts_allow_7_13": pts_allowed(7, 13),
    "pts_allow_14_20": pts_allowed(14, 20),
    "pts_allow_21_27": pts_allowed(21, 27),
    "pts_allow_28_34": pts_allowed(28, 34),
    "pts_allow_35p": pts_allowed(35),
}


# Sleeper's default half-PPR rules: the fixed scoring used to backtest and calibrate the
# model. Ranges are fit in this scoring and applied to every league (a v1 simplification).
REFERENCE_RULES: dict[str, float] = {
    "pass_yd": 0.04, "pass_td": 4, "pass_int": -1, "pass_2pt": 2,
    "rush_yd": 0.1, "rush_td": 6, "rush_2pt": 2,
    "rec": 0.5, "rec_yd": 0.1, "rec_td": 6, "rec_2pt": 2,
    "fum_lost": -2, "fum_rec_td": 6, "st_td": 6,
    "fgm_0_19": 3, "fgm_20_29": 3, "fgm_30_39": 3, "fgm_40_49": 4, "fgm_50p": 5,
    "xpm": 1, "fgmiss": -1, "xpmiss": -1,
    "sack": 1, "int": 2, "fum_rec": 2, "def_td": 6, "safe": 2, "blk_kick": 2, "def_st_td": 6,
    "pts_allow_0": 10, "pts_allow_1_6": 7, "pts_allow_7_13": 4, "pts_allow_14_20": 1,
    "pts_allow_21_27": 0, "pts_allow_28_34": -1, "pts_allow_35p": -4,
}  # fmt: skip


@dataclass(frozen=True)
class RuleCheck:
    supported: dict[str, float]
    unsupported: dict[str, float]  # non-zero rules we can't score yet (shown, not hidden)


def check_rules(rules: Mapping[str, float]) -> RuleCheck:
    supported: dict[str, float] = {}
    unsupported: dict[str, float] = {}
    for key, value in rules.items():
        if not value:
            continue  # omitted or zero rules score nothing
        (supported if key in SLEEPER_RULES else unsupported)[key] = float(value)
    return RuleCheck(supported, unsupported)


def scoring_key(rules: Mapping[str, float]) -> str:
    """Stable hash of the rules that matter: leagues with identical scoring share projections."""
    nonzero = {k: round(float(v), 6) for k, v in sorted(rules.items()) if v}
    return hashlib.sha256(json.dumps(nonzero, sort_keys=True).encode()).hexdigest()[:16]


def score(df: pd.DataFrame, rules: Mapping[str, float]) -> pd.Series:
    """Fantasy points for every row of `df` (needs a `position` column + stat columns)."""
    pts = pd.Series(0.0, index=df.index)
    position = df["position"]
    for key, value in check_rules(rules).supported.items():
        rule = SLEEPER_RULES[key]
        applies = position.isin(rule.positions)
        if rule.only_position:
            applies &= position == rule.only_position
        if not applies.any():
            continue
        q = rule.quantity(df).astype(float)
        if rule.shape == "per_unit":
            contrib = q * value
        elif rule.shape == "tier":
            contrib = (q >= rule.lo).astype(float) * value
        else:
            contrib = ((q >= rule.lo) & (q <= rule.hi)).astype(float) * value
        pts = pts + np.where(applies, contrib, 0.0)
    return pts.round(2)


def score_one(stats: Mapping[str, float], position: str, rules: Mapping[str, float]) -> float:
    df = pd.DataFrame([{**stats, "position": position}])
    return float(score(df, rules).iloc[0])
