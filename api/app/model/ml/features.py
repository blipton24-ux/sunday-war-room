"""The feature table (P4 step 4, ADR-060): one row per player-week, every value known before
that week's kickoff.

`build_features(data, targets)` serves the backtest (targets = every past player-game) and the
live compute (targets = this week's players), so a signal is computed one way only.

How "before kickoff" is kept:
- A player's, team's and defense's running totals are taken from their latest game **strictly
  before** the projected week (`pd.merge_asof(..., allow_exact_matches=False)`).
- This week's pre-game facts (betting line, roof, home or away, rest, injury report, depth chart)
  are matched to the projected week itself; later weeks are never read.
- "Season" values reset each season; "recent" is the last three games, across a season break;
  "last" is the whole previous season.
The leak test (tests/unit/test_ml_features.py) changes everything from the projected week on and
checks that no row moves.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from app.model.ml.data import ModelData

SKILL = ("QB", "RB", "WR", "TE")
RECENT_GAMES = 3
EARLY_WEEKS = 4
TARGET_COLUMNS = ("gsis_id", "season", "week", "position", "team", "opponent")
WINDOWS = ("recent", "season", "last")

# Raw stat columns summed per player (a missing column counts as zero).
PLAYER_SUMS = (
    "targets", "receptions", "receiving_yards", "receiving_tds", "receiving_air_yards",
    "carries", "rushing_yards", "rushing_tds",
    "attempts", "completions", "passing_yards", "passing_tds", "passing_interceptions",
    "sacks_suffered",
)  # fmt: skip
TEAM_SUMS = ("targets", "carries", "receiving_air_yards", "attempts", "sacks_suffered")
WINDOW_SUMS = (
    *PLAYER_SUMS, *(f"team_{c}" for c in TEAM_SUMS), "snap_sum", "snap_n", "games",
)  # fmt: skip
# What a defense allows to one position, per game.
ALLOWED_BY_POSITION = (
    "targets",
    "receiving_yards",
    "receiving_tds",
    "carries",
    "rushing_yards",
    "rushing_tds",
)
# What a defense allows through the air, all positions together.
ALLOWED_PASSING = ("attempts", "passing_yards", "passing_tds", "passing_interceptions",
                   "sacks_suffered")  # fmt: skip

REPORT_CODES = {"Questionable": 1.0, "Doubtful": 2.0, "Out": 3.0}
PRACTICE_CODES = {
    "Full Participation in Practice": 1.0,
    "Limited Participation in Practice": 2.0,
    "Did Not Participate In Practice": 3.0,
}
UNAVAILABLE = frozenset({"Out", "Doubtful"})
DOME_ROOFS = frozenset({"dome", "closed"})
KNOWN_ROOFS = frozenset({"dome", "closed", "open", "outdoors"})


def _t(df: pd.DataFrame) -> pd.Series:
    """A sortable week key: 2023 week 11 -> 202311."""
    return df["season"].astype(int) * 100 + df["week"].astype(int)


def _ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    return (num / den.where(den > 0)).astype(float)


def _asof(left: pd.DataFrame, right: pd.DataFrame, by: list[str], prefix: str = "") -> pd.DataFrame:
    """For each left row, the latest right row with a strictly earlier week key `t`.
    `right` carries `t` and `game_season` (the season of that row)."""
    cols = {c: f"{prefix}{c}" for c in right.columns if c not in (*by, "t")}
    # One key type on both sides: an empty frame (no reserve-list rows yet) comes back as
    # plain objects while a filled one holds strings, and merge_asof refuses to mix them.
    left = left.astype({b: "string" for b in by})
    right = right.astype({b: "string" for b in by})
    merged = pd.merge_asof(
        left.sort_values("t"),
        right.sort_values("t").rename(columns=cols),
        on="t",
        by=by,
        allow_exact_matches=False,
        direction="backward",
    )
    return merged


def _windows(table: pd.DataFrame, by: list[str], sums: tuple[str, ...]) -> pd.DataFrame:
    """Running totals after each row (sorted by `t` within `by`): last RECENT_GAMES rows, and
    season to date. Returns by + t + game_season + recent_* + season_*."""
    table = table.sort_values([*by, "t"]).reset_index(drop=True)
    recent = (
        table.groupby(by)[list(sums)]
        .rolling(RECENT_GAMES, min_periods=1)
        .sum()
        .reset_index(level=list(range(len(by))), drop=True)
        .sort_index()
    )
    season = table.groupby([*by, "season"])[list(sums)].cumsum()
    out = table[[*by, "t"]].copy()
    out["game_season"] = table["season"].to_numpy()
    for c in sums:
        out[f"recent_{c}"] = recent[c].to_numpy()
        out[f"season_{c}"] = season[c].to_numpy()
    return out


def _season_only(merged: pd.DataFrame, target_season: pd.Series, columns: list[str]) -> None:
    """Season-to-date values from an earlier season mean "no games yet this season"."""
    stale = merged["game_season"].to_numpy() != target_season.to_numpy()
    merged.loc[stale, columns] = np.nan


# --------------------------------------------------------------------------- players
def player_games(stats: pd.DataFrame) -> pd.DataFrame:
    """Skill-position player-games with the sums the windows read, and team totals per game."""
    s = stats[stats["position"].isin(SKILL)].copy()
    for c in PLAYER_SUMS:
        s[c] = s[c].fillna(0.0).astype(float) if c in s.columns else 0.0
    team = s.groupby(["team", "season", "week"])[list(TEAM_SUMS)].transform("sum")
    for c in TEAM_SUMS:
        s[f"team_{c}"] = team[c]
    snap = s["snap"].astype(float) if "snap" in s.columns else pd.Series(np.nan, index=s.index)
    s["snap_sum"] = snap.fillna(0.0)
    s["snap_n"] = snap.notna().astype(float)
    s["games"] = 1.0
    s["t"] = _t(s)
    return s.reset_index(drop=True)


def _rates(out: pd.DataFrame, src: pd.DataFrame, w: str) -> None:
    """Role and efficiency columns for one window from its sums (`src` columns `{w}_{sum}`)."""

    def c(name: str) -> pd.Series:
        return src[f"{w}_{name}"]

    out[f"{w}_games"] = c("games").fillna(0.0)
    out[f"{w}_target_share"] = _ratio(c("targets"), c("team_targets"))
    out[f"{w}_carry_share"] = _ratio(c("carries"), c("team_carries"))
    out[f"{w}_air_share"] = _ratio(c("receiving_air_yards"), c("team_receiving_air_yards"))
    out[f"{w}_attempt_share"] = _ratio(c("attempts"), c("team_attempts"))
    out[f"{w}_snap_share"] = _ratio(c("snap_sum"), c("snap_n"))
    out[f"{w}_targets_pg"] = _ratio(c("targets"), c("games"))
    out[f"{w}_carries_pg"] = _ratio(c("carries"), c("games"))
    out[f"{w}_attempts_pg"] = _ratio(c("attempts"), c("games"))
    out[f"{w}_targets"] = c("targets")
    out[f"{w}_carries"] = c("carries")
    out[f"{w}_attempts"] = c("attempts")
    out[f"{w}_catch_rate"] = _ratio(c("receptions"), c("targets"))
    out[f"{w}_yards_per_target"] = _ratio(c("receiving_yards"), c("targets"))
    out[f"{w}_yards_per_catch"] = _ratio(c("receiving_yards"), c("receptions"))
    out[f"{w}_rec_td_rate"] = _ratio(c("receiving_tds"), c("targets"))
    out[f"{w}_yards_per_carry"] = _ratio(c("rushing_yards"), c("carries"))
    out[f"{w}_rush_td_rate"] = _ratio(c("rushing_tds"), c("carries"))
    out[f"{w}_completion_rate"] = _ratio(c("completions"), c("attempts"))
    out[f"{w}_yards_per_attempt"] = _ratio(c("passing_yards"), c("attempts"))
    out[f"{w}_pass_td_rate"] = _ratio(c("passing_tds"), c("attempts"))
    out[f"{w}_int_rate"] = _ratio(c("passing_interceptions"), c("attempts"))
    out[f"{w}_sack_rate"] = _ratio(c("sacks_suffered"), c("attempts") + c("sacks_suffered"))


def _player_features(games: pd.DataFrame, tg: pd.DataFrame) -> pd.DataFrame:
    win = _windows(games, ["gsis_id"], WINDOW_SUMS)
    last_team = games[["gsis_id", "t", "team"]].rename(columns={"team": "last_team"})
    win = win.merge(last_team, on=["gsis_id", "t"], how="left")
    m = _asof(tg[["_row", "gsis_id", "t", "season", "week"]], win, ["gsis_id"])
    season_cols = [f"season_{c}" for c in WINDOW_SUMS]
    _season_only(m, m["season"], season_cols)

    # the previous season's totals, by player
    last = games.groupby(["gsis_id", "season"])[list(WINDOW_SUMS)].sum().reset_index()
    last = last.rename(columns={c: f"last_{c}" for c in WINDOW_SUMS})
    last["season"] = last["season"] + 1
    m = m.merge(last, on=["gsis_id", "season"], how="left")

    out = pd.DataFrame({"_row": m["_row"].to_numpy()})
    for w in WINDOWS:
        _rates(out, m, w)
    for name in ("target_share", "carry_share", "snap_share"):
        out[f"{name}_trend"] = _ratio(out[f"recent_{name}"], out[f"season_{name}"])
    out["season_games"] = out["season_games"].fillna(0.0)
    out["last_games"] = out["last_games"].fillna(0.0)
    return out.set_index("_row")


# --------------------------------------------------------------------------- teams
def _team_features(games: pd.DataFrame, game_rows: pd.DataFrame, tg: pd.DataFrame) -> pd.DataFrame:
    per = games.groupby(["team", "season", "week"])[["attempts", "sacks_suffered", "carries"]].sum()
    per = per.reset_index()
    per["dropbacks"] = per["attempts"] + per["sacks_suffered"]
    per["plays"] = per["dropbacks"] + per["carries"]
    scores = _team_sides(game_rows)[["team", "season", "week", "points_for"]]
    per = per.merge(scores, on=["team", "season", "week"], how="left")
    per["points_for"] = per["points_for"].fillna(0.0)
    per["games"] = 1.0
    per["t"] = _t(per)
    sums = ("plays", "dropbacks", "points_for", "games")
    win = _windows(per, ["team"], sums)
    m = _asof(tg[["_row", "team", "t", "season"]], win, ["team"])
    _season_only(m, m["season"], [f"season_{c}" for c in sums])
    out = pd.DataFrame({"_row": m["_row"].to_numpy()})
    for w in ("recent", "season"):
        out[f"team_plays_pg_{w}"] = _ratio(m[f"{w}_plays"], m[f"{w}_games"])
        out[f"team_pass_rate_{w}"] = _ratio(m[f"{w}_dropbacks"], m[f"{w}_plays"])
        out[f"team_points_pg_{w}"] = _ratio(m[f"{w}_points_for"], m[f"{w}_games"])
    return out.set_index("_row")


# --------------------------------------------------------------------------- opponents
def _opponent_features(games: pd.DataFrame, tg: pd.DataFrame) -> pd.DataFrame:
    played = games[["opponent", "season", "week"]].drop_duplicates()
    grid = played.merge(pd.DataFrame({"position": list(SKILL)}), how="cross")
    by_pos = games.groupby(["opponent", "season", "week", "position"])[
        list(ALLOWED_BY_POSITION)
    ].sum()
    grid = grid.merge(by_pos.reset_index(), on=["opponent", "season", "week", "position"],
                      how="left").fillna({c: 0.0 for c in ALLOWED_BY_POSITION})  # fmt: skip
    grid["games"] = 1.0
    grid["t"] = _t(grid)
    sums = (*ALLOWED_BY_POSITION, "games")
    win = _windows(grid, ["opponent", "position"], sums)
    m = _asof(tg[["_row", "opponent", "position", "t", "season"]], win, ["opponent", "position"])
    _season_only(m, m["season"], [f"season_{c}" for c in sums])
    out = pd.DataFrame({"_row": m["_row"].to_numpy()})
    for w in ("recent", "season"):
        for c in ALLOWED_BY_POSITION:
            out[f"opp_{c}_pg_{w}"] = _ratio(m[f"{w}_{c}"], m[f"{w}_games"])

    passing = games.groupby(["opponent", "season", "week"])[list(ALLOWED_PASSING)].sum()
    passing = passing.reset_index()
    passing["games"] = 1.0
    passing["t"] = _t(passing)
    psums = (*ALLOWED_PASSING, "games")
    pwin = _windows(passing, ["opponent"], psums)
    p = _asof(tg[["_row", "opponent", "t", "season"]], pwin, ["opponent"])
    _season_only(p, p["season"], [f"season_{c}" for c in psums])
    p = p.set_index("_row").loc[out["_row"]]
    for w in ("recent", "season"):
        out[f"opp_passing_yards_pg_{w}"] = _ratio(
            p[f"{w}_passing_yards"], p[f"{w}_games"]
        ).to_numpy()
        out[f"opp_pass_td_rate_{w}"] = _ratio(p[f"{w}_passing_tds"], p[f"{w}_attempts"]).to_numpy()
        out[f"opp_int_rate_{w}"] = _ratio(
            p[f"{w}_passing_interceptions"], p[f"{w}_attempts"]
        ).to_numpy()
        out[f"opp_sack_rate_{w}"] = _ratio(
            p[f"{w}_sacks_suffered"], p[f"{w}_attempts"] + p[f"{w}_sacks_suffered"]
        ).to_numpy()
    return out.set_index("_row")


# --------------------------------------------------------------------------- game context
def _team_sides(game_rows: pd.DataFrame) -> pd.DataFrame:
    """One row per team per game: spread from the team's side (positive: favoured), implied
    scores, roof, kickoff, and the final score (read only for earlier games)."""
    sides = []
    for home in (True, False):
        me, other = ("home", "away") if home else ("away", "home")
        sign = 1.0 if home else -1.0
        g = game_rows
        side = pd.DataFrame(
            {
                "season": g["season"].astype(int),
                "week": g["week"].astype(int),
                "team": g[me],
                "home": float(home),
                "spread": g["spread_line"].astype(float) * sign,
                "total": g["total_line"].astype(float),
                "roof": g["roof"],
                "kickoff_at": pd.to_datetime(g["kickoff_at"], utc=True),
                "points_for": g[f"{me}_score"].astype(float),
            }
        )
        side["implied_team"] = side["total"] / 2 + side["spread"] / 2
        side["implied_opponent"] = side["total"] / 2 - side["spread"] / 2
        side["opponent_team"] = g[other].to_numpy()
        sides.append(side)
    out = pd.concat(sides, ignore_index=True).sort_values(["team", "kickoff_at"])
    prev = out.groupby(["team", "season"])["kickoff_at"].shift(1)
    out["rest_days"] = (out["kickoff_at"] - prev).dt.total_seconds() / 86400.0
    return out


def _game_features(game_rows: pd.DataFrame, tg: pd.DataFrame) -> pd.DataFrame:
    sides = _team_sides(game_rows)
    m = tg[["_row", "team", "season", "week"]].merge(
        sides[["team", "season", "week", "home", "spread", "total", "implied_team",
               "implied_opponent", "roof", "rest_days", "kickoff_at"]],
        on=["team", "season", "week"], how="left",
    )  # fmt: skip
    roof = m["roof"]
    known = roof.isin(KNOWN_ROOFS)
    out = pd.DataFrame(
        {
            "_row": m["_row"],
            "home": m["home"],
            "spread": m["spread"],
            "total": m["total"],
            "implied_team": m["implied_team"],
            "implied_opponent": m["implied_opponent"],
            "dome": np.where(known, roof.isin(DOME_ROOFS).astype(float), np.nan),
            "rest_days": m["rest_days"],
            "week_of_season": m["week"].astype(float),
            "early_season": (m["week"] <= EARLY_WEEKS).astype(float),
            "kickoff_at": m["kickoff_at"],
        }
    )
    return out.set_index("_row")


# --------------------------------------------------------------------------- availability
def _availability(data: ModelData, games: pd.DataFrame, tg: pd.DataFrame) -> pd.DataFrame:
    inj = data.injuries.copy()
    out = pd.DataFrame({"_row": tg["_row"].to_numpy()}).set_index("_row")
    if inj.empty:
        inj = pd.DataFrame(columns=["gsis_id", "season", "week", "report_status",
                                    "roster_status", "practice_status"])  # fmt: skip
    inj["season"] = inj["season"].astype(int)
    inj["week"] = inj["week"].astype(int)

    this_week = (
        tg[["_row", "gsis_id", "season", "week"]]
        .merge(inj, on=["gsis_id", "season", "week"], how="left")
        .drop_duplicates("_row")
        .set_index("_row")
    )
    out["report_status"] = this_week["report_status"].map(REPORT_CODES).fillna(0.0)
    out["practice_status"] = this_week["practice_status"].map(PRACTICE_CODES).fillna(0.0)
    out["on_reserve"] = (this_week["roster_status"] == "RES").astype(float)

    # weeks since his last game this season, and back from a reserve list since then
    last = games[["gsis_id", "t", "season", "week"]].rename(
        columns={"season": "game_season", "week": "last_week"}
    )
    lg = _asof(tg[["_row", "gsis_id", "t", "season", "week"]], last, ["gsis_id"]).set_index("_row")
    same = lg["game_season"] == lg["season"]
    lg["last_t"] = (lg["season"] * 100 + lg["last_week"]).where(same)  # his last game this season
    out["weeks_since_last_game"] = (lg["week"] - lg["last_week"]).where(same)
    reserve = inj[inj["roster_status"] == "RES"][["gsis_id", "season", "week"]].copy()
    reserve["t"] = _t(reserve)
    reserve["reserve_t"] = reserve["t"]
    reserve = reserve[["gsis_id", "t", "reserve_t"]]
    rs = _asof(tg[["_row", "gsis_id", "t", "season"]], reserve, ["gsis_id"]).set_index("_row")
    season_start = rs["season"] * 100
    after_last = rs["reserve_t"] > lg.loc[rs.index, "last_t"].fillna(season_start)
    out["back_from_reserve"] = (after_last & (rs["reserve_t"] > season_start)).astype(float)

    depth = data.depth[["gsis_id", "season", "week", "depth_tier"]]
    d = (
        tg[["_row", "gsis_id", "season", "week"]]
        .merge(depth, on=["gsis_id", "season", "week"], how="left")
        .drop_duplicates("_row")
        .set_index("_row")
    )
    out["depth_tier"] = d["depth_tier"].astype(float)

    out["out_teammate_share"] = _out_teammate_share(inj, games, tg)
    return out


def _out_teammate_share(inj: pd.DataFrame, games: pd.DataFrame, tg: pd.DataFrame) -> pd.Series:
    """Share of the team's opportunities this season (targets and carries; pass attempts for
    quarterbacks) held by same-position teammates listed Out or Doubtful, or on a reserve list,
    that week. Their team and share are as of their last game before that week."""
    gone = inj[inj["report_status"].isin(UNAVAILABLE) | (inj["roster_status"] == "RES")]
    gone = gone[["gsis_id", "season", "week"]].drop_duplicates()
    empty = pd.Series(0.0, index=pd.Index(tg["_row"].to_numpy(), name="_row"))
    if gone.empty:
        return empty
    gone = gone.assign(t=_t(gone))
    sums = ("targets", "carries", "attempts", "team_targets", "team_carries", "team_attempts")
    win = _windows(games, ["gsis_id"], sums)
    pos_team = games[["gsis_id", "t", "team", "position"]]
    win = win.merge(pos_team, on=["gsis_id", "t"], how="left")
    keep = ["gsis_id", "t", "game_season", "team", "position", *(f"season_{c}" for c in sums)]
    g = _asof(gone, win[keep], ["gsis_id"])
    g = g[g["game_season"] == g["season"]]
    qb = g["position"] == "QB"
    share = np.where(
        qb,
        _ratio(g["season_attempts"], g["season_team_attempts"]),
        _ratio(g["season_targets"] + g["season_carries"],
               g["season_team_targets"] + g["season_team_carries"]),
    )  # fmt: skip
    g = g.assign(share=np.nan_to_num(share))
    m = tg[["_row", "gsis_id", "team", "position", "season", "week"]].merge(
        g[["gsis_id", "team", "position", "season", "week", "share"]].rename(
            columns={"gsis_id": "mate"}
        ),
        on=["team", "position", "season", "week"],
        how="left",
    )
    m = m[m["mate"] != m["gsis_id"]]
    total = m.groupby("_row")["share"].sum()
    return total.reindex(empty.index).fillna(0.0)


# --------------------------------------------------------------------------- background
def _background(data: ModelData, tg: pd.DataFrame, kickoff: pd.Series) -> pd.DataFrame:
    bg = data.background.drop_duplicates("gsis_id")
    m = tg[["_row", "gsis_id", "season", "week"]].merge(bg, on="gsis_id", how="left")
    m = m.set_index("_row")
    approx = [
        date(int(s), 9, 7) + timedelta(days=7 * (int(w) - 1))
        for s, w in zip(m["season"], m["week"], strict=True)
    ]
    when = pd.to_datetime(kickoff.reindex(m.index)).dt.tz_localize(None).dt.normalize()
    when = when.fillna(pd.Series(pd.to_datetime(approx), index=m.index))
    born = pd.to_datetime(m["birth_date"])
    out = pd.DataFrame(index=m.index)
    out["age"] = (when - born).dt.days / 365.25
    out["years_in_league"] = (m["season"] - m["rookie_season"]).astype(float)
    out["draft_round"] = m["draft_round"].astype(float)
    out["draft_pick"] = m["draft_pick"].astype(float)
    known = m["rookie_season"].notna() | m["birth_date"].notna()
    out["undrafted"] = np.where(known, m["draft_round"].isna().astype(float), np.nan)
    return out


# --------------------------------------------------------------------------- the table
def build_features(data: ModelData, targets: pd.DataFrame) -> pd.DataFrame:
    """`targets`: TARGET_COLUMNS, one row per player-week to project (skill positions).
    Returns `targets` (same order) plus every model input (`feature_columns`)."""
    missing = set(TARGET_COLUMNS) - set(targets.columns)
    if missing:
        raise ValueError(f"targets is missing {sorted(missing)}")
    tg = targets.reset_index(drop=True).copy()
    tg["season"] = tg["season"].astype(int)
    tg["week"] = tg["week"].astype(int)
    tg["_row"] = np.arange(len(tg))
    tg["t"] = _t(tg)

    games = player_games(data.stats)
    game_rows = data.games
    parts = [
        _player_features(games, tg),
        _team_features(games, game_rows, tg),
        _opponent_features(games, tg),
    ]
    context = _game_features(game_rows, tg)
    parts += [
        context.drop(columns=["kickoff_at"]),
        _availability(data, games, tg),
        _background(data, tg, context["kickoff_at"]),
    ]
    features = pd.concat([p.reindex(tg["_row"]) for p in parts], axis=1)
    out = pd.concat([targets.reset_index(drop=True), features.reset_index(drop=True)], axis=1)
    return out


def feature_columns(table: pd.DataFrame) -> list[str]:
    """The model inputs: every column `build_features` adds."""
    return [c for c in table.columns if c not in TARGET_COLUMNS]
