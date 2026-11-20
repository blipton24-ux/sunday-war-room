"""ADR-068: whether a player on the injury report took an offensive snap that week."""

import polars as pl

from app.services.ingest import mark_played


def test_played_comes_from_snap_counts_and_stays_unknown_before_they_exist() -> None:
    injuries = pl.DataFrame(
        {"gsis_id": ["a", "b", "c", "a"], "season": [2025, 2025, 2025, 2025],
         "week": [3, 3, 3, 4], "report_status": ["Questionable"] * 4}
    )  # fmt: skip
    snaps = pl.DataFrame(
        {"gsis_id": ["a", "c", "x"], "season": [2025, 2025, 2025], "week": [3, 3, 3],
         "offense_pct": [0.71, 0.0, 0.5]}
    )  # fmt: skip
    out = mark_played(injuries, snaps)
    # a played; b had no snap row; c only played special teams; week 4 has no snap counts yet
    assert out["played"].to_list() == [True, False, False, None]
    assert out.columns == [*injuries.columns, "played"]
