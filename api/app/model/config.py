"""Switches for the projection model (P4, ADR-054).

Every idea being tested is one or two fields here, neutral by default. `SHIPPED` is what live
code runs, so it only changes in the same commit that bumps MODEL_VERSION. The backtest builds a
candidate from the shipped config plus one idea and compares the two. Names in `CANDIDATES` are
what `python -m app.scripts.backtest --compare shipped,<name>` accepts; join names with `+`
to stack ideas (`shipped,xfp-blend+implied-total`). The ledger ids (E-02, ...) are in
docs/Build-Plan/Model-Experiments.md.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from typing import Any


@dataclass(frozen=True)
class ModelConfig:
    # -- shipped constants, as fields so they can be tuned (H) ----------------------------------
    half_life: float = 4.0  # a game this many games ago counts half as much as the latest
    prior_games: float = 3.0  # last season's average counts like this many games
    prior_games_opener: float | None = None  # E-17: a different weight for weeks 1-4
    half_life_by_position: tuple[tuple[str, float], ...] = ()  # E-26
    prior_games_by_position: tuple[tuple[str, float], ...] = ()  # E-27
    opp_clamp: float = 0.25  # E-10: opponent effect limit
    opp_fade_games: float = 4.0  # E-10: opponent effect weight n / (n + this)
    role_clamp: float = 0.15  # E-18
    role_window: int = 2  # E-18: games in the recent snap share

    # -- A. opportunity -----------------------------------------------------------------------
    xfp_weight: float = 0.0  # E-02: share of the baseline built from expected points (volume)
    td_regression: float = 0.0  # E-03: share of touchdown points replaced by the expected amount
    usage_trend: bool = False  # E-05: target / carry share trend replaces the snap-share role

    # -- B. defense against each position -----------------------------------------------------
    def_pass: bool = False  # E-06: passing game allowed to the position, not total points
    def_run: bool = False  # E-07: rushing allowed to the position
    def_sack_int: float = 0.0  # E-08: quarterback effect of the opponent's sack / interception rate
    def_schedule_adjust: bool = False  # E-09: allowed points relative to who the defense faced

    # -- C. offense quality -------------------------------------------------------------------
    team_offense: float = 0.0  # E-11: weight on the team's scoring strength
    implied_total: float = 0.0  # E-12: weight on the betting market's implied team score
    game_script: float = 0.0  # E-13: favourites run more, underdogs pass more (per spread point)

    # -- D. role and depth --------------------------------------------------------------------
    rookie_prior: bool = False  # E-16: no-history starting value from draft round

    # -- E. injuries --------------------------------------------------------------------------
    skip_injury_games_in_history: bool = False  # E-01 (dropped)

    # -- F. game conditions -------------------------------------------------------------------
    home_boost: float = 0.0  # E-21: +x at home, -x away
    wind_penalty: float = 0.0  # E-22: passing / kicking effect of wind above 12 mph
    rest_effect: float = 0.0  # E-23: short week -x, long rest +x

    # -- G. kickers and defenses --------------------------------------------------------------
    kicker_model: float = 0.0  # E-24: weight on the team's implied score
    defense_model: float = 0.0  # E-25: weight on the opponent's implied score

    # -- per position (ADR-055: an idea can be kept for the positions it helps only) ------------
    # position -> the fields that differ for that position, e.g. (("WR", (("xfp_weight", 0.5),)),)
    overrides: tuple[tuple[str, tuple[tuple[str, Any], ...]], ...] = ()

    def for_position(self, position: str) -> ModelConfig:
        """The settings one position runs with (no overrides left inside)."""
        changes = dict(dict(self.overrides).get(position, ()))
        return replace(self, overrides=(), **changes)

    def with_override(self, positions: tuple[str, ...], changes: dict[str, Any]) -> ModelConfig:
        merged = {pos: dict(vals) for pos, vals in self.overrides}
        for pos in positions:
            merged.setdefault(pos, {}).update(changes)
        packed = tuple((pos, tuple(sorted(vals.items()))) for pos, vals in sorted(merged.items()))
        return replace(self, overrides=packed)

    @property
    def needs_extras(self) -> bool:
        return bool(
            self.team_offense or self.implied_total or self.game_script or self.rookie_prior
            or self.home_boost or self.wind_penalty or self.rest_effect
            or self.kicker_model or self.defense_model
        )  # fmt: skip

    @property
    def needs_raw_stats(self) -> bool:
        return bool(
            self.xfp_weight or self.td_regression or self.usage_trend or self.def_pass
            or self.def_run or self.def_sack_int or self.def_schedule_adjust
        )  # fmt: skip

    def half_life_for(self, position: str) -> float:
        return dict(self.half_life_by_position).get(position, self.half_life)

    def prior_games_for(self, position: str, week: int) -> float:
        by_pos = dict(self.prior_games_by_position)
        if week <= 4 and self.prior_games_opener is not None:
            return self.prior_games_opener
        return by_pos.get(position, self.prior_games)


SHIPPED = ModelConfig()

CANDIDATES: dict[str, ModelConfig] = {
    "shipped": SHIPPED,
    # E-01 (dropped)
    "skip-injury-history": replace(SHIPPED, skip_injury_games_in_history=True),
    # A. opportunity
    "xfp-blend": replace(SHIPPED, xfp_weight=0.5),
    "xfp-blend-25": replace(SHIPPED, xfp_weight=0.25),
    "xfp-blend-75": replace(SHIPPED, xfp_weight=0.75),
    "td-regression": replace(SHIPPED, td_regression=0.5),
    "td-regression-full": replace(SHIPPED, td_regression=1.0),
    "usage-trend": replace(SHIPPED, usage_trend=True),
    # B. defense against each position
    "def-pass-position": replace(SHIPPED, def_pass=True),
    "def-run-position": replace(SHIPPED, def_run=True),
    "def-sack-int": replace(SHIPPED, def_sack_int=0.25),
    "def-schedule-adjust": replace(SHIPPED, def_schedule_adjust=True),
    "opp-shrink": replace(SHIPPED, opp_fade_games=8.0, opp_clamp=0.4),
    "opp-shrink-soft": replace(SHIPPED, opp_fade_games=12.0, opp_clamp=0.5),
    # C. offense quality
    "team-offense": replace(SHIPPED, team_offense=0.5),
    "team-offense-25": replace(SHIPPED, team_offense=0.25),
    "implied-total": replace(SHIPPED, implied_total=0.6),
    "implied-total-30": replace(SHIPPED, implied_total=0.3),
    "game-script": replace(SHIPPED, game_script=0.01),
    # D. role and depth
    "rookie-prior": replace(SHIPPED, rookie_prior=True),
    "opener-weights": replace(SHIPPED, prior_games_opener=6.0),
    "opener-weights-low": replace(SHIPPED, prior_games_opener=1.5),
    "role-window": replace(SHIPPED, role_window=3, role_clamp=0.25),
    # F. game conditions
    "home-away": replace(SHIPPED, home_boost=0.03),
    "roof-weather": replace(SHIPPED, wind_penalty=0.05),
    "rest-days": replace(SHIPPED, rest_effect=0.03),
    # G. kickers and defenses
    "kicker-model": replace(SHIPPED, kicker_model=0.6),
    "defense-model": replace(SHIPPED, defense_model=0.6),
    # H. how the pieces combine
    "halflife-2": replace(SHIPPED, half_life=2.0),
    "halflife-3": replace(SHIPPED, half_life=3.0),
    "halflife-6": replace(SHIPPED, half_life=6.0),
    "halflife-10": replace(SHIPPED, half_life=10.0),
    "prior-games-1": replace(SHIPPED, prior_games=1.0),
    "prior-games-2": replace(SHIPPED, prior_games=2.0),
    "prior-games-5": replace(SHIPPED, prior_games=5.0),
}


def _parse_value(field_name: str, text: str) -> Any:
    default = getattr(SHIPPED, field_name)
    if text.lower() == "none":
        return None
    if isinstance(default, bool):
        return text.lower() in ("true", "1", "yes")
    if isinstance(default, int):
        return int(text)
    return float(text)


def _changes(token: str) -> dict[str, Any]:
    """A candidate name, or `field=value` for any numeric or on/off field."""
    names = {f.name for f in fields(ModelConfig)} - {"overrides"}
    if "=" in token:
        field_name, value = (x.strip() for x in token.split("=", 1))
        if field_name not in names:
            raise SystemExit(f"Unknown model setting {field_name!r}")
        return {field_name: _parse_value(field_name, value)}
    try:
        candidate = CANDIDATES[token]
    except KeyError:
        raise SystemExit(
            f"Unknown model config {token!r}. Known: {', '.join(CANDIDATES)}"
        ) from None
    return {n: getattr(candidate, n) for n in names if getattr(candidate, n) != getattr(SHIPPED, n)}


def by_name(name: str) -> ModelConfig:
    """Parts joined with `+`. Each part is a candidate name or `field=value`, and may end in
    `@QB/RB` to apply to those positions only: `xfp_weight=0.5@WR/TE+implied-total`."""
    config = SHIPPED
    for part in name.split("+"):
        token, _, where = part.strip().partition("@")
        changes = _changes(token.strip())
        if where:
            config = config.with_override(tuple(p.strip() for p in where.split("/")), changes)
        elif changes:
            config = replace(config, **changes)
    return config
