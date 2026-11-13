"""Injury-game marking (ADR-054): evidence-based, no hindsight, strict on purpose."""

from typing import Any

import pandas as pd

from app.model.features.injury_games import EXCLUDED, excluded, mark_injury_games


def games(
    player: str, snaps: list[float | None], team: str = "AAA", season: int = 2025
) -> list[dict[str, Any]]:
    return [
        {"gsis_id": player, "season": season, "week": w, "team": team, "snap": s}
        for w, s in enumerate(snaps, start=1)
    ]


def injuries(*rows: tuple[str, int, str | None, str | None]) -> pd.DataFrame:
    """(player, week, report_status, roster_status)."""
    return pd.DataFrame(
        [
            {"gsis_id": p, "season": 2025, "week": w, "report_status": r, "roster_status": rs}
            for p, w, r, rs in rows
        ]
    )


def label(
    history: list[dict[str, Any]],
    inj: pd.DataFrame | None,
    player: str,
    week: int,
    season: int = 2025,
) -> Any:
    df = pd.DataFrame(history)
    marks = mark_injury_games(df, inj)
    row = (df["gsis_id"] == player) & (df["week"] == week) & (df["season"] == season)
    return marks[row].iloc[0]


# A starter who normally plays 80%, then 20% in week 5; the team plays every week.
STARTER = [0.8, 0.8, 0.8, 0.8, 0.2, 0.8, 0.8]


def test_snap_collapse_plus_a_report_designation_at_the_next_game_is_during() -> None:
    inj = injuries(("p1", 6, "Out", None))
    assert label(games("p1", STARTER), inj, "p1", 5) == "during"


def test_snap_collapse_plus_a_reserve_listing_is_during() -> None:
    """Injured reserve is on the roster list, not the report."""
    inj = injuries(("p1", 6, None, "RES"))
    assert label(games("p1", STARTER), inj, "p1", 5) == "during"


def test_a_benching_is_not_an_injury() -> None:
    """Snaps fell but nothing says he is hurt: a demotion or a blowout, so the game counts."""
    assert label(games("p1", STARTER), injuries(("p1", 6, None, None)), "p1", 5) is None
    assert label(games("p1", STARTER), None, "p1", 5) is None


def test_evidence_must_be_at_the_next_game_not_later() -> None:
    inj = injuries(("p1", 7, "Out", None))  # a different, later problem
    assert label(games("p1", STARTER), inj, "p1", 5) is None


def test_an_injury_report_without_a_snap_collapse_is_not_marked() -> None:
    inj = injuries(("p1", 4, "Out", None))
    assert label(games("p1", [0.8, 0.8, 0.8, 0.7, 0.75, 0.8]), inj, "p1", 3) is None


def test_backups_and_players_without_history_are_not_marked() -> None:
    inj = injuries(("p1", 6, "Out", None), ("p2", 3, "Out", None))
    backup = games("p1", [0.2, 0.2, 0.2, 0.2, 0.05, 0.2])  # normal 20% is below the floor
    rookie = games("p2", [0.9, 0.1])  # only one earlier game
    assert label(backup, inj, "p1", 5) is None
    assert label(rookie, inj, "p2", 2) is None


def test_kickers_and_defenses_have_no_snap_share_and_never_get_during() -> None:
    inj = injuries(("k1", 6, "Out", None))
    assert label(games("k1", [None] * 7), inj, "k1", 5) is None


def test_listed_out_but_played_is_before_and_questionable_who_played_is_kept_apart() -> None:
    hist = games("p1", [0.8] * 6)
    inj = injuries(("p1", 3, "Doubtful", None), ("p1", 4, "Questionable", None))
    assert label(hist, inj, "p1", 3) == "before"
    assert label(hist, inj, "p1", 4) == "questionable"
    assert not excluded(pd.Series(["questionable"])).any()  # reported, not left out
    assert excluded(pd.Series(["before", "during"])).all()
    assert {"before", "during"} == EXCLUDED


def test_a_bye_week_looks_to_the_teams_next_game_week() -> None:
    hist = [r for r in games("p1", STARTER) if r["week"] != 6]  # the team is off in week 6
    inj = injuries(("p1", 7, "Out", None))  # so week 7 is the next game
    assert label(hist, inj, "p1", 5) == "during"


def test_marking_never_looks_at_whether_the_player_played_later() -> None:
    """No hindsight: dropping every game he plays after the injury leaves the mark unchanged."""
    full = games("p1", STARTER) + games("p2", [0.5] * 7)  # a teammate keeps the team's weeks
    inj = injuries(("p1", 6, "Out", None))
    before = label(full, inj, "p1", 5)
    trimmed = [r for r in full if not (r["gsis_id"] == "p1" and r["week"] > 5)]
    assert before == label(trimmed, inj, "p1", 5) == "during"


def test_last_seasons_games_count_towards_a_players_normal() -> None:
    last = games("p1", [0.8, 0.8], season=2024)
    this = games("p1", [0.2, 0.8], season=2025)  # week 1 collapses against last season's normal
    inj = injuries(("p1", 2, "Out", None))
    assert label(last + this, inj, "p1", 1) == "during"


def test_empty_inputs_mark_nothing() -> None:
    assert mark_injury_games(pd.DataFrame(columns=["gsis_id"]), None).empty
    assert label(games("p1", STARTER), pd.DataFrame(), "p1", 5) is None
