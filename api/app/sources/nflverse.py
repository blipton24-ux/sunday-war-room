"""The ONLY module that reads nflverse (via nflreadpy). Everything else gets clean frames.

Schema contracts: each loader checks the columns Sunday War Room depends on and raises
`NflverseSchemaError` if one is missing (fail loudly). It never falls back to another season.
Legitimately missing values (a player with no snaps) stay null (fail softly).

Outputs are polars DataFrames with Sunday War Room column names and canonical team codes.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import nflreadpy as nfl
import polars as pl

from app.logging import get_logger
from app.nfl_teams import canonical_team, defense_key

log = get_logger("nflverse")

FANTASY_POSITIONS = ("QB", "RB", "WR", "TE", "K")

# Columns the scoring map (app/model/scoring.py) and the model read. Contract for load_player_stats.
PLAYER_STAT_COLUMNS: tuple[str, ...] = (
    "completions", "attempts", "passing_yards", "passing_tds", "passing_interceptions",
    "sacks_suffered", "sack_fumbles_lost", "passing_2pt_conversions", "passing_first_downs",
    "carries", "rushing_yards", "rushing_tds", "rushing_fumbles_lost", "rushing_first_downs",
    "rushing_2pt_conversions",
    "receptions", "targets", "receiving_yards", "receiving_tds", "receiving_fumbles_lost",
    "receiving_first_downs", "receiving_2pt_conversions",
    "special_teams_tds", "fumble_recovery_tds", "fumbles_total", "fumbles_lost_total",
    "punt_return_yards", "kickoff_return_yards",
    "fg_made", "fg_att", "fg_missed",
    "fg_made_0_19", "fg_made_20_29", "fg_made_30_39", "fg_made_40_49", "fg_made_50_59",
    "fg_made_60_", "fg_missed_0_19", "fg_missed_20_29", "fg_missed_30_39", "fg_missed_40_49",
    "fg_missed_50_59", "fg_missed_60_", "pat_made", "pat_att", "pat_missed",
)  # fmt: skip
PLAYER_KEY_COLUMNS = ("player_id", "player_display_name", "position", "season", "week",
                      "season_type", "team", "opponent_team")  # fmt: skip

TEAM_DEF_COLUMNS: tuple[str, ...] = (
    "def_sacks", "def_interceptions", "fumble_recovery_opp", "def_fumbles_forced", "def_tds",
    "def_safeties", "def_fg_blocks", "def_punt_blocks", "def_pat_blocks", "special_teams_tds",
    "fumble_recovery_tds",
)  # fmt: skip
TEAM_KEY_COLUMNS = ("team", "opponent_team", "season", "week", "season_type")

SCHEDULE_COLUMNS = ("game_id", "season", "game_type", "week", "gameday", "gametime",
                    "home_team", "away_team", "home_score", "away_score")  # fmt: skip
SNAP_COLUMNS = ("pfr_player_id", "season", "week", "game_type", "offense_pct")
ROSTER_COLUMNS = ("season", "week", "game_type", "gsis_id", "status")
GAME_CONTEXT_COLUMNS = ("season", "game_type", "week", "home_team", "away_team", "spread_line",
                        "total_line", "roof", "temp", "wind", "home_rest", "away_rest",
                        "home_score", "away_score")  # fmt: skip
DRAFT_COLUMNS = ("season", "round", "pick", "gsis_id", "position")
INJURY_COLUMNS = ("season", "game_type", "week", "gsis_id", "report_status", "practice_status",
                  "report_primary_injury", "date_modified")  # fmt: skip
ID_COLUMNS = ("gsis_id", "sleeper_id", "espn_id", "yahoo_id", "pfr_id", "name", "position")


class NflverseSchemaError(RuntimeError):
    """An nflverse file no longer has a column we depend on."""


def current_season() -> int:
    """The NFL season nflverse considers current (rolls over in the spring)."""
    return int(nfl.get_current_season())


def check_columns(df: pl.DataFrame, required: Iterable[str], what: str) -> None:
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise NflverseSchemaError(f"nflverse {what} is missing columns: {missing}")


def _check_seasons(df: pl.DataFrame, seasons: Sequence[int], what: str) -> None:
    """Every requested season must be present: never silently train on fewer seasons."""
    got = set(df["season"].unique().to_list()) if df.height else set()
    absent = sorted(set(seasons) - got)
    if absent:
        raise NflverseSchemaError(f"nflverse {what} has no rows for seasons {absent}")


def _canon(col: str) -> pl.Expr:
    return pl.col(col).map_elements(canonical_team, return_dtype=pl.String)


# --------------------------------------------------------------------------- weekly stats
def load_player_stats(seasons: Sequence[int]) -> pl.DataFrame:
    """Regular-season weekly offense + kicker stats, one row per player-week."""
    raw = nfl.load_player_stats(list(seasons))
    check_columns(raw, PLAYER_KEY_COLUMNS + PLAYER_STAT_COLUMNS, "player_stats")
    _check_seasons(raw, seasons, "player_stats")
    df = raw.filter(
        (pl.col("season_type") == "REG")
        & pl.col("player_id").is_not_null()
        & pl.col("position").is_in(FANTASY_POSITIONS)
    )
    return df.select(
        pl.col("player_id").alias("gsis_id"),
        pl.col("player_display_name").alias("name"),
        "position",
        "season",
        "week",
        "season_type",
        _canon("team").alias("team"),
        _canon("opponent_team").alias("opponent"),
        *[pl.col(c).cast(pl.Float64).fill_null(0.0) for c in PLAYER_STAT_COLUMNS],
    )


def load_defense_stats(seasons: Sequence[int], schedule: pl.DataFrame) -> pl.DataFrame:
    """Team-defense weekly rows, shaped like player rows (gsis_id = TEAM_<abbr>, position DEF).

    `points_allowed` comes from the final score in the schedule.
    """
    raw = nfl.load_team_stats(list(seasons))
    check_columns(raw, TEAM_KEY_COLUMNS + TEAM_DEF_COLUMNS, "team_stats")
    _check_seasons(raw, seasons, "team_stats")
    df = raw.filter(pl.col("season_type") == "REG").select(
        "season",
        "week",
        _canon("team").alias("team"),
        _canon("opponent_team").alias("opponent"),
        *[pl.col(c).cast(pl.Float64).fill_null(0.0) for c in TEAM_DEF_COLUMNS],
    )
    allowed = pl.concat(
        [
            schedule.select(
                "season", "week", pl.col("home").alias("team"),
                pl.col("away_score").cast(pl.Float64).alias("points_allowed"),
            ),
            schedule.select(
                "season", "week", pl.col("away").alias("team"),
                pl.col("home_score").cast(pl.Float64).alias("points_allowed"),
            ),
        ]
    )  # fmt: skip
    df = df.join(allowed, on=["season", "week", "team"], how="left")
    return df.with_columns(
        pl.col("team").map_elements(defense_key, return_dtype=pl.String).alias("gsis_id"),
        pl.lit("DEF").alias("position"),
        pl.col("team").alias("name"),
        pl.lit("REG").alias("season_type"),
    )


# --------------------------------------------------------------------------- schedule
def load_schedule(seasons: Sequence[int]) -> pl.DataFrame:
    """Regular-season games with kickoff as UTC (nflverse times are US/Eastern)."""
    raw = nfl.load_schedules(list(seasons))
    check_columns(raw, SCHEDULE_COLUMNS, "schedules")
    _check_seasons(raw, seasons, "schedules")
    return raw.filter(pl.col("game_type") == "REG").select(
        "game_id",
        "season",
        "week",
        pl.col("game_type"),
        _canon("home_team").alias("home"),
        _canon("away_team").alias("away"),
        (pl.col("gameday") + " " + pl.col("gametime"))
        .str.strptime(pl.Datetime("us"), "%Y-%m-%d %H:%M", strict=False)
        .dt.replace_time_zone("America/New_York")
        .dt.convert_time_zone("UTC")
        .alias("kickoff_at"),
        pl.col("home_score").cast(pl.Int32),
        pl.col("away_score").cast(pl.Int32),
    )


def load_game_context(seasons: Sequence[int]) -> pl.DataFrame:
    """Pre-game betting lines and conditions, one row per team per regular-season game (P4).

    `spread` is from the team's side (positive: favoured by that many points), `implied` is the
    team's implied score from the spread and the total, `rest` the days since its last game.
    `points_for` / `points_against` are the final score, for rolling team strength; they are
    only ever read for games before the week being projected.
    """
    raw = nfl.load_schedules(list(seasons))
    check_columns(raw, GAME_CONTEXT_COLUMNS, "schedules")
    _check_seasons(raw, seasons, "schedules")
    games = raw.filter(pl.col("game_type") == "REG")
    common = ["season", "week", "roof", "temp", "wind", "total_line"]

    def side(home: bool) -> pl.DataFrame:
        me, other = ("home", "away") if home else ("away", "home")
        sign = 1.0 if home else -1.0
        return games.select(
            *common,
            _canon(f"{me}_team").alias("team"),
            _canon(f"{other}_team").alias("opponent"),
            pl.lit(home).alias("home"),
            (pl.col("spread_line") * sign).alias("spread"),
            (pl.col("total_line") / 2 + pl.col("spread_line") * sign / 2).alias("implied"),
            pl.col(f"{me}_rest").alias("rest"),
            pl.col(f"{me}_score").cast(pl.Float64).alias("points_for"),
            pl.col(f"{other}_score").cast(pl.Float64).alias("points_against"),
        )

    return pl.concat([side(True), side(False)]).rename({"total_line": "total"})


def load_draft_capital(seasons: Sequence[int]) -> pl.DataFrame:
    """Draft round and pick for every drafted player in `seasons` (the year he was drafted)."""
    raw = nfl.load_draft_picks(list(seasons))
    check_columns(raw, DRAFT_COLUMNS, "draft_picks")
    return raw.filter(pl.col("gsis_id").is_not_null()).select(
        "gsis_id", pl.col("season").alias("draft_year"), "round", "pick"
    )


# Expected stats per game (nflverse ff_opportunity), renamed to the stat names the scoring map
# reads, so a league's own rules turn them into expected fantasy points.
EXPECTED_STAT_COLUMNS = {
    "pass_attempt": "attempts", "rush_attempt": "carries", "rec_attempt": "targets",
    "pass_completions_exp": "completions", "pass_yards_gained_exp": "passing_yards",
    "pass_touchdown_exp": "passing_tds", "pass_interception_exp": "passing_interceptions",
    "pass_two_point_conv_exp": "passing_2pt_conversions",
    "pass_first_down_exp": "passing_first_downs",
    "rush_yards_gained_exp": "rushing_yards", "rush_touchdown_exp": "rushing_tds",
    "rush_two_point_conv_exp": "rushing_2pt_conversions",
    "rush_first_down_exp": "rushing_first_downs",
    "receptions_exp": "receptions", "rec_yards_gained_exp": "receiving_yards",
    "rec_touchdown_exp": "receiving_tds", "rec_two_point_conv_exp": "receiving_2pt_conversions",
    "rec_first_down_exp": "receiving_first_downs",
}  # fmt: skip
DEPTH_POSITIONS = ("QB", "RB", "WR", "TE")
DEPTH_TIERS = 3  # starter, next in line, deeper
WR_TIER_LIMITS = (3, 5)  # 2025+ format: WR1-3 are starters, WR4-5 next in line


def load_expected_stats(seasons: Sequence[int]) -> pl.DataFrame:
    """What an average player would have produced from each player's opportunities, per game
    (P4, E-04). Opportunity counts are real; yards, catches and touchdowns are nflverse's
    expected values given where and how each play happened (down, distance, field position,
    air yards). One row per player-game: gsis_id, season, week and EXPECTED_STAT_COLUMNS' names."""
    raw = nfl.load_ff_opportunity(list(seasons))
    check_columns(raw, ("season", "week", "player_id", *EXPECTED_STAT_COLUMNS), "ff_opportunity")
    return raw.filter(pl.col("player_id").is_not_null()).select(
        pl.col("player_id").alias("gsis_id"),
        pl.col("season").cast(pl.Int64),
        pl.col("week").cast(pl.Int64),
        *(pl.col(src).cast(pl.Float64).fill_null(0.0).alias(dst)
          for src, dst in EXPECTED_STAT_COLUMNS.items()),
    )  # fmt: skip


def _tier(position: pl.Expr, rank: pl.Expr) -> pl.Expr:
    """Depth tier 1-3 from a straight-down rank (2025+ format)."""
    wr = (
        pl.when(rank <= WR_TIER_LIMITS[0])
        .then(1)
        .when(rank <= WR_TIER_LIMITS[1])
        .then(2)
        .otherwise(3)
    )
    return pl.when(position == "WR").then(wr).otherwise(pl.min_horizontal(rank, DEPTH_TIERS))


def load_depth_tiers(seasons: Sequence[int]) -> pl.DataFrame:
    """Each offensive player's depth-chart tier the week of each game (P4, E-14): 1 starter,
    2 next in line, 3 deeper. One row per player-week: gsis_id, season, week, depth_tier.

    Up to 2024 nflverse publishes a chart per week, where several receivers share level 1 (one
    per formation slot): the tier is that level. From 2025 it publishes dated snapshots that
    number players straight down; a week uses the last snapshot taken before the day of its
    first kickoff, so nothing from game day or later is read.
    """
    frames = []
    weekly = [s for s in seasons if s <= 2024]
    if weekly:
        raw = nfl.load_depth_charts(weekly)
        check_columns(
            raw, ("season", "week", "game_type", "gsis_id", "depth_team", "depth_position",
                  "formation"), "depth_charts",
        )  # fmt: skip
        frames.append(
            raw.filter(
                (pl.col("game_type") == "REG")
                & (pl.col("formation") == "Offense")
                & pl.col("gsis_id").is_not_null()
                & pl.col("depth_position").is_in(DEPTH_POSITIONS)
            )
            .group_by(["gsis_id", "season", "week"])
            .agg(pl.col("depth_team").cast(pl.Int64, strict=False).min().alias("depth_tier"))
            .with_columns(pl.min_horizontal("depth_tier", DEPTH_TIERS).alias("depth_tier"))
            .select(
                "gsis_id",
                pl.col("season").cast(pl.Int64),
                pl.col("week").cast(pl.Int64),
                pl.col("depth_tier").cast(pl.Int64),
            )
        )
    snapshots = [s for s in seasons if s >= 2025]
    if snapshots:
        games = nfl.load_schedules(snapshots).filter(pl.col("game_type") == "REG")
        first_day = games.group_by(["season", "week"]).agg(pl.col("gameday").min())
    for season in snapshots:
        raw = nfl.load_depth_charts([season])
        check_columns(raw, ("dt", "gsis_id", "pos_abb", "pos_rank"), "depth_charts")
        charts = raw.filter(
            pl.col("gsis_id").is_not_null() & pl.col("pos_abb").is_in(DEPTH_POSITIONS)
        )
        stamps = charts.select("dt").unique().sort("dt")["dt"].to_list()
        days = first_day.filter(pl.col("season") == season).sort("week").rows(named=True)
        pick = []
        for day in days:
            before = [d for d in stamps if d < str(day["gameday"])]
            if before:
                pick.append({"week": int(day["week"]), "dt": before[-1]})
        if not pick:
            continue
        chosen = charts.join(pl.DataFrame(pick), on="dt")
        frames.append(
            chosen.group_by(["gsis_id", "week", "pos_abb"])
            .agg(pl.col("pos_rank").min())
            .with_columns(_tier(pl.col("pos_abb"), pl.col("pos_rank")).alias("depth_tier"))
            .group_by(["gsis_id", "week"])
            .agg(pl.col("depth_tier").min())
            .select(
                "gsis_id",
                pl.lit(season, pl.Int64).alias("season"),
                pl.col("week").cast(pl.Int64),
                pl.col("depth_tier").cast(pl.Int64),
            )
        )
    if not frames:
        return pl.DataFrame(
            schema={"gsis_id": pl.String, "season": pl.Int64, "week": pl.Int64,
                    "depth_tier": pl.Int64}
        )  # fmt: skip
    return pl.concat(frames)


# --------------------------------------------------------------------------- snaps + ids
def load_snap_shares(seasons: Sequence[int], ids: pl.DataFrame) -> pl.DataFrame:
    """Offensive snap share per player-week, mapped from PFR ids to gsis ids."""
    raw = nfl.load_snap_counts(list(seasons))
    check_columns(raw, SNAP_COLUMNS, "snap_counts")
    pfr = ids.filter(pl.col("pfr_id").is_not_null()).select("pfr_id", "gsis_id")
    return (
        raw.filter(pl.col("game_type") == "REG")
        .join(pfr, left_on="pfr_player_id", right_on="pfr_id", how="inner")
        .select("gsis_id", "season", "week", pl.col("offense_pct").cast(pl.Float64))
        .unique(subset=["gsis_id", "season", "week"], keep="first")
    )


def load_injury_reports(seasons: Sequence[int]) -> pl.DataFrame:
    """Weekly game-status injury reports, one row per player-week (regular season).

    nflverse lists each practice day as its own row; the game designation (Out, Doubtful,
    Questionable) is the latest one the team filed that week. Players on the report with no
    designation keep a null `report_status`. Players on a reserve list that week (the weekly
    roster status `RES`, which includes injured reserve and is visible the week the placement
    happens, unlike the report) carry `roster_status = "RES"`.
    """
    raw = nfl.load_injuries(list(seasons))
    check_columns(raw, INJURY_COLUMNS, "injuries")
    _check_seasons(raw, seasons, "injuries")
    reports = (
        raw.filter((pl.col("game_type") == "REG") & pl.col("gsis_id").is_not_null())
        .sort("date_modified")
        .group_by(["gsis_id", "season", "week"], maintain_order=True)
        .agg(
            pl.col("report_status").drop_nulls().last().alias("report_status"),
            pl.col("practice_status").drop_nulls().last().alias("practice_status"),
            pl.col("report_primary_injury").drop_nulls().last().alias("injury"),
        )
    )
    rosters = nfl.load_rosters_weekly(list(seasons))
    check_columns(rosters, ROSTER_COLUMNS, "rosters_weekly")
    _check_seasons(rosters, seasons, "rosters_weekly")
    reserve = (
        rosters.filter(
            (pl.col("game_type") == "REG")
            & pl.col("gsis_id").is_not_null()
            & (pl.col("status") == "RES")
        )
        .select("gsis_id", "season", "week", pl.lit("RES").alias("roster_status"))
        .unique(subset=["gsis_id", "season", "week"])
    )
    return reports.join(reserve, on=["gsis_id", "season", "week"], how="full", coalesce=True)


def load_id_crosswalk() -> pl.DataFrame:
    """gsis <-> sleeper/espn/yahoo/pfr ids. Ambiguous rows are dropped, never guessed.

    A sleeper_id or gsis_id that appears on more than one row is excluded (logged), because
    linking it to the wrong player would silently project the wrong person.
    """
    raw = nfl.load_ff_playerids()
    check_columns(raw, ID_COLUMNS, "ff_playerids")
    df = raw.select(
        pl.col("gsis_id").cast(pl.String),
        pl.col("sleeper_id").cast(pl.String),
        pl.col("espn_id").cast(pl.String),
        pl.col("yahoo_id").cast(pl.String),
        pl.col("pfr_id").cast(pl.String),
        "name",
        "position",
    ).filter(pl.col("gsis_id").is_not_null())
    before = df.height
    for key in ("gsis_id", "sleeper_id", "pfr_id"):
        dupes = (
            df.filter(pl.col(key).is_not_null()).group_by(key).len().filter(pl.col("len") > 1)[key]
        )
        if dupes.len():
            log.warning("crosswalk_ambiguous_ids", key=key, ids=dupes.to_list()[:20])
            df = df.filter(~pl.col(key).is_in(dupes.implode()) | pl.col(key).is_null())
    log.info("crosswalk_loaded", rows=df.height, dropped=before - df.height)
    return df
