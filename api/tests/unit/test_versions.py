"""Which projection a screen shows when more than one model version has a row (M-01)."""

from datetime import UTC, datetime, timedelta

from app.db.models import Projection
from app.services.versions import MIXED, choose_projections, shown_version

T0 = datetime(2026, 11, 1, tzinfo=UTC)


def row(player: int, version: str, frozen: bool, minutes: int = 0, points: float = 1.0):
    return Projection(
        player_id=player,
        season=2026,
        week=9,
        scoring_key="k",
        points=points,
        p10=0.0,
        p50=points,
        p90=2.0,
        factors=[],
        model_version=version,
        computed_at=T0 + timedelta(minutes=minutes),
        frozen=frozen,
    )


def test_a_frozen_row_from_an_older_version_beats_a_fresh_current_row() -> None:
    rows = [row(1, "1.0.0", True, points=10.0), row(1, "1.1.0", False, minutes=5, points=12.0)]
    assert choose_projections(rows, "1.1.0")[1].points == 10.0


def test_without_a_frozen_row_the_current_version_wins_even_if_older_rows_are_newer() -> None:
    rows = [row(1, "1.1.0", False, minutes=0, points=12.0), row(1, "1.0.0", False, minutes=9)]
    assert choose_projections(rows, "1.1.0")[1].points == 12.0


def test_failing_both_the_newest_row_is_used() -> None:
    rows = [
        row(1, "0.8.0", False, minutes=0, points=3.0),
        row(1, "0.9.0", False, minutes=4, points=4.0),
    ]
    assert choose_projections(rows, "1.1.0")[1].points == 4.0


def test_players_are_chosen_independently() -> None:
    rows = [row(1, "1.0.0", True), row(2, "1.1.0", False)]
    chosen = choose_projections(rows, "1.1.0")
    assert chosen[1].model_version == "1.0.0" and chosen[2].model_version == "1.1.0"


def test_the_label_names_one_version_or_says_mixed() -> None:
    assert shown_version([], "1.1.0") == "1.1.0"
    assert shown_version([row(1, "1.0.0", True), row(2, "1.0.0", True)], "1.1.0") == "1.0.0"
    assert shown_version([row(1, "1.0.0", True), row(2, "1.1.0", False)], "1.1.0") == MIXED
