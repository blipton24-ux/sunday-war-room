"""ESPN's numeric team ids and D/ST ids map onto our canonical team codes (P3 step 3)."""

from __future__ import annotations

import pytest

from app.adapters.espn_teams import all_pro_team_codes, defense_team, team_for_pro_team_id
from app.nfl_teams import NFL_TEAMS
from app.services.player_ids import normalize_name


def test_every_nfl_team_is_covered_exactly_once() -> None:
    assert all_pro_team_codes() == set(NFL_TEAMS)  # 32 teams, no gaps, no strays


@pytest.mark.parametrize(
    ("pro_team_id", "team"),
    [(1, "ATL"), (14, "LA"), (28, "WAS"), (30, "JAX"), (13, "LV"), (34, "HOU")],
)
def test_pro_team_ids_use_our_spelling(pro_team_id: int, team: str) -> None:
    assert team_for_pro_team_id(pro_team_id) == team


def test_free_agents_and_unknown_ids_have_no_team() -> None:
    assert team_for_pro_team_id(0) is None
    assert team_for_pro_team_id(99) is None


@pytest.mark.parametrize(
    ("espn_id", "team"), [("-16001", "ATL"), ("-16028", "WAS"), ("-16014", "LA")]
)
def test_defense_ids_map_to_their_team(espn_id: str, team: str) -> None:
    assert defense_team(espn_id) == team


@pytest.mark.parametrize("espn_id", ["3916387", "0", "abc", "-1", "-16099"])
def test_other_ids_are_not_defenses(espn_id: str) -> None:
    assert defense_team(espn_id) is None


def test_names_compare_without_case_punctuation_or_suffixes() -> None:
    assert normalize_name("Odell Beckham Jr.") == normalize_name("odell beckham")
    assert normalize_name("D.J. Moore") == normalize_name("DJ Moore")
    assert normalize_name("Amon-Ra St. Brown") == "amon ra st brown"
    assert normalize_name("Marvin Harrison II") == "marvin harrison"
