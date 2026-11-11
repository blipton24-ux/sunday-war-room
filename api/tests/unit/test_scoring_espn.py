"""ESPN scoring rules scored with our own stats (P3 steps 7-8, ADR-053)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from app.model.scoring import check_rules, score, scoring_key
from app.model.scoring_espn import (
    ESPN_RULES,
    HEAD_COACH,
    IDP,
    NOT_IN_DATA,
    PREFIX,
    PUNTER,
    RATES,
    SLOT_POSITION,
    STAT_ABBR,
    STAT_COUNT,
    TOUCHDOWN_GROUPS,
    abbr_for,
    expand_espn,
    unsupported_reason,
)
from app.sources.nflverse import PLAYER_STAT_COLUMNS, TEAM_DEF_COLUMNS


def stat_id(abbr: str) -> int:
    return next(i for i, a in STAT_ABBR.items() if a == abbr)


def items(**abbr_points: float) -> list[dict[str, Any]]:
    return [{"statId": stat_id(a.replace("_", "")), "points": p} for a, p in abbr_points.items()]


def pts(position: str, rules: dict[str, float], **stats: float) -> float:
    df = pd.DataFrame([{**stats, "position": position}])
    return float(score(df, rules).iloc[0])


# --------------------------------------------------------------------------- the catalogue
def test_the_stat_table_covers_ids_0_to_234_without_repeats() -> None:
    assert sorted(STAT_ABBR) == list(range(STAT_COUNT))
    assert len(set(STAT_ABBR.values())) == STAT_COUNT


def test_every_espn_rule_is_scored_or_explained() -> None:
    """ESPN's whole catalogue: each stat is scored, a touchdown-group member, or explained."""
    grouped = {m for members in TOUCHDOWN_GROUPS.values() for m in members}
    explained = IDP | PUNTER | HEAD_COACH | RATES | NOT_IN_DATA
    for stat, abbr in STAT_ABBR.items():
        scored = PREFIX + abbr in ESPN_RULES
        assert scored or abbr in grouped or abbr in explained, f"stat {stat} ({abbr}) is neither"
        if not scored:
            assert unsupported_reason(PREFIX + abbr) != unsupported_reason("espn:NOPE"), abbr


def test_a_scored_rule_is_not_also_listed_as_unscorable() -> None:
    explained = IDP | PUNTER | HEAD_COACH | RATES | NOT_IN_DATA
    assert not {a for a in STAT_ABBR.values() if PREFIX + a in ESPN_RULES} & explained


class Probe:
    """Records which stat columns a rule reads (rules default a missing column to zero)."""

    def __init__(self) -> None:
        self.index = pd.RangeIndex(1)
        self.read: set[str] = set()

    def get(self, name: str, default: pd.Series) -> pd.Series:
        self.read.add(name)
        return default


def test_every_rule_reads_only_columns_our_stats_carry() -> None:
    """A rule on a column we don't load would silently score zero; it must be unsupported."""
    known = set(PLAYER_STAT_COLUMNS) | set(TEAM_DEF_COLUMNS) | {"points_allowed", "attempts"}
    for key, rule in ESPN_RULES.items():
        probe = Probe()
        rule.quantity(probe)  # type: ignore[arg-type]
        assert probe.read <= known, f"{key} reads unknown columns {probe.read - known}"


def test_unknown_stat_ids_are_kept_and_reported_never_dropped() -> None:
    rules = expand_espn([{"statId": 999, "points": 2.0}])
    assert rules == {"espn:STAT999": 2.0}
    assert check_rules(rules).unsupported == {"espn:STAT999": 2.0}
    assert abbr_for(999) == "STAT999"


@pytest.mark.parametrize(
    ("abbr", "words"),
    [("TK", "defensive players"), ("PTY", "Punters"), ("TW", "Head coaches"), ("CPCT", "rate"),
     ("YA399", "free stat feeds"), ("INTTD", "touchdowns")],
)  # fmt: skip
def test_unsupported_rules_say_why(abbr: str, words: str) -> None:
    assert words in unsupported_reason(f"espn:{abbr}")


# --------------------------------------------------------------------------- the shapes
def test_per_unit_passing_and_receiving() -> None:
    rules = expand_espn(items(PY=0.04, PTD=4, INTT=-2, REC=1, REY=0.1, RETD=6))
    assert pts("QB", rules, passing_yards=300, passing_tds=2, passing_interceptions=1) == 18.0
    assert pts("WR", rules, receptions=7, receiving_yards=82, receiving_tds=1) == 21.2


def test_step_rules_count_whole_steps_per_game_toward_zero() -> None:
    rules = expand_espn(items(RY10=1))
    assert pts("RB", rules, rushing_yards=57) == 5.0  # 57 yards is five whole tens
    assert pts("RB", rules, rushing_yards=9) == 0.0
    assert pts("RB", rules, rushing_yards=-12) == -1.0  # cut toward zero, not floored to -2
    assert pts("QB", expand_espn(items(PY25=1)), passing_yards=300) == 12.0


def test_every_100_yards_is_a_step_but_a_100_yard_game_is_a_bonus() -> None:
    step = expand_espn(items(R100=1))  # "every 100 rushing yards"
    bonus = expand_espn(items(RY100=3))  # "100-199 yard rushing game"
    assert pts("RB", step, rushing_yards=250) == 2.0
    assert pts("RB", bonus, rushing_yards=250) == 0.0  # 250 is outside 100-199, literally
    assert pts("RB", bonus, rushing_yards=150) == 3.0


def test_game_bonuses_are_literal_ranges() -> None:
    only_300 = expand_espn(items(P300=3))
    both = expand_espn(items(P300=3, P400=5))
    assert pts("QB", only_300, passing_yards=320) == 3.0
    assert pts("QB", only_300, passing_yards=420) == 0.0  # a 420-yard game earns nothing from P300
    assert pts("QB", both, passing_yards=420) == 5.0


def test_points_allowed_tiers_are_literal_and_a_missing_tier_scores_nothing() -> None:
    rules = expand_espn(items(PA0=10, PA1=7, PA7=4, PA14=1, PA28=-1, PA35=-4))  # no PA18/PA22
    assert pts("DEF", rules, points_allowed=0) == 10.0
    assert pts("DEF", rules, points_allowed=10) == 4.0
    assert pts("DEF", rules, points_allowed=20) == 0.0  # 18-21 isn't configured: scores nothing
    assert pts("DEF", rules, points_allowed=24) == 0.0
    assert pts("DEF", rules, points_allowed=40) == -4.0  # PA35 covers 35-45
    assert pts("DEF", rules, points_allowed=50) == 0.0  # 46+ is its own tier, not configured


def test_defense_counts() -> None:
    rules = expand_espn(items(SK=1, INT=2, FR=2, SF=2))
    got = pts("DEF", rules, def_sacks=3, def_interceptions=1, fumble_recovery_opp=1, def_safeties=1)
    assert got == 3 + 2 + 2 + 2


# --------------------------------------------------------------------------- kicking ladders
def test_the_last_configured_field_goal_band_covers_every_longer_kick() -> None:
    rules = expand_espn(items(FG0=3, FG40=4, FG50=5))  # no FG60
    assert "espn:FG50+" in rules and "espn:FG50" not in rules
    none = {"fg_made_0_19": 0, "fg_made_20_29": 0, "fg_made_30_39": 0, "fg_made_40_49": 0}
    assert pts("K", rules, **none, fg_made_50_59=1) == 5.0
    assert pts("K", rules, **none, fg_made_60_=1) == 5.0  # a 62-yarder scores at the 50+ value
    assert pts("K", rules, **{**none, "fg_made_40_49": 1}) == 4.0


def test_with_an_explicit_60_band_the_50_band_stays_50_to_59() -> None:
    rules = expand_espn(items(FG50=5, FG60=7))
    assert "espn:FG50" in rules and "espn:FG50+" not in rules
    base = {"fg_made_50_59": 0, "fg_made_60_": 0}
    assert pts("K", rules, **{**base, "fg_made_50_59": 1}) == 5.0
    assert pts("K", rules, **{**base, "fg_made_60_": 1}) == 7.0


def test_a_single_low_band_absorbs_all_kicks_and_missed_kicks_follow_the_same_rule() -> None:
    rules = expand_espn(items(FG0=3, FGM0=-1))
    assert "espn:FG0+" in rules and "espn:FGM0+" in rules
    assert pts("K", rules, fg_made_0_19=1, fg_made_50_59=1, fg_missed_40_49=1) == 3 + 3 - 1


def test_kicker_totals_and_extra_points() -> None:
    rules = expand_espn(items(FG=3, PAT=1, FGM=-1, PATM=-1))
    stats = {"fg_made": 2, "pat_made": 3, "fg_missed": 1, "pat_missed": 0}
    assert pts("K", rules, **stats) == 6 + 3 - 1


# --------------------------------------------------------------------------- per-position values
def test_a_tight_end_premium_override_replaces_the_base_value_for_tes_only() -> None:
    raw = [{"statId": stat_id("REC"), "points": 1.0, "pointsOverrides": {"6": 1.5}}]
    rules = expand_espn(raw)
    assert rules == {"espn:REC": 1.0, "espn:REC@TE": 1.5}
    assert pts("TE", rules, receptions=4) == 6.0  # 4 x 1.5, not 4 x 1.0 + 4 x 1.5
    assert pts("WR", rules, receptions=4) == 4.0
    assert pts("RB", rules, receptions=4) == 4.0


def test_a_zero_base_with_a_defense_override_scores_only_the_defense() -> None:
    raw = [{"statId": stat_id("SK"), "points": 0, "pointsOverrides": {"16": 1.0}}]
    rules = expand_espn(raw)
    assert rules == {"espn:SK@DEF": 1.0}
    assert pts("DEF", rules, def_sacks=3) == 3.0


def test_a_zero_override_switches_a_rule_off_for_that_position() -> None:
    rules = expand_espn([{"statId": stat_id("REC"), "points": 1.0, "pointsOverrides": {"2": 0}}])
    assert "espn:REC@RB" in rules  # kept even though it is zero
    assert pts("RB", rules, receptions=5) == 0.0
    assert pts("WR", rules, receptions=5) == 5.0


def test_an_override_for_a_slot_we_cannot_name_is_reported() -> None:
    rules = expand_espn([{"statId": stat_id("REC"), "points": 1.0, "pointsOverrides": {"23": 2.0}}])
    assert "espn:REC@SLOT23" in check_rules(rules).unsupported
    assert SLOT_POSITION[16] == "DEF"


def test_a_zero_override_changes_the_scoring_key_but_other_zero_rules_do_not() -> None:
    base = {"espn:REC": 1.0}
    assert scoring_key(base) == scoring_key({**base, "espn:PY": 0.0})
    assert scoring_key(base) != scoring_key({**base, "espn:REC@RB": 0.0})
    assert scoring_key({"pass_yd": 0.04}) == scoring_key({"pass_yd": 0.04, "rec": 0.0})  # Sleeper


# --------------------------------------------------------------------------- touchdown groups
def test_members_sharing_a_value_score_the_team_touchdown_total_once() -> None:
    rules = expand_espn(items(INTTD=6, FRTD=6, BLKKRTD=6))
    assert rules == {"espn:def_tds": 6.0}
    assert pts("DEF", rules, def_tds=1) == 6.0  # one pick-six is 6 points, not 18


def test_members_with_different_values_are_reported_not_guessed() -> None:
    rules = expand_espn(items(INTTD=6, FRTD=4))
    assert set(check_rules(rules).unsupported) == {"espn:INTTD", "espn:FRTD"}
    assert pts("DEF", rules, def_tds=1) == 0.0
    assert "touchdowns" in unsupported_reason("espn:INTTD")


def test_special_teams_touchdowns_score_for_players_and_defenses() -> None:
    rules = expand_espn(items(KRTD=6, PRTD=6))
    assert rules == {"espn:special_teams_tds": 6.0}
    assert pts("WR", rules, special_teams_tds=1) == 6.0
    assert pts("DEF", rules, special_teams_tds=1) == 6.0


# --------------------------------------------------------------------------- engine invariants
def test_unsupported_espn_rules_never_score_and_are_listed() -> None:
    rules = expand_espn(items(TK=1, PY=0.04, YA399=2))
    check = check_rules(rules)
    assert set(check.unsupported) == {"espn:TK", "espn:YA399"}
    assert pts("QB", rules, passing_yards=250) == 10.0


def test_a_position_outside_a_rules_scope_never_scores_it() -> None:
    rules = expand_espn(items(SK=1, REC=1))
    assert pts("WR", rules, def_sacks=5, receptions=2) == 2.0  # sacks are a defense rule
    assert pts("DEF", rules, def_sacks=5, receptions=2) == 5.0
