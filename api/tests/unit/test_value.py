"""Value engine (P2 step 3): best lineups, team value, waivers value added, trade impact."""

import random

import pytest

from app.model.lineup import LineupPlayer, optimal_lineup
from app.model.value import (
    ValuePlayer,
    best_lineup_points,
    fit_to_limit,
    roster_limit,
    starting_slots,
    suggest_trades,
    team_value,
    trade_impact,
    waiver_gains,
)

STANDARD = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF", "BN", "BN", "BN", "BN"]
SLOT_MIXES = {
    "standard": STANDARD,
    "superflex": ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "SUPER_FLEX", "BN", "BN"],
    "2qb": ["QB", "QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "BN"],
    "overlapping flexes": ["QB", "RB", "WR", "TE", "REC_FLEX", "WRRB_FLEX", "WRRB_FLEX", "BN"],
    "no kicker or defense": ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "FLEX", "BN"],
    "ir and taxi": ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "BN", "BN", "IR", "TAXI"],
}
ONE_WEEK = {1: 1.0}


def vp(pid: int, pos: str, *points: float, **kw: bool) -> ValuePlayer:
    """A player with `points` in weeks 1, 2, 3..."""
    return ValuePlayer(pid, pos, {w: p for w, p in enumerate(points, start=1)}, **kw)


# --------------------------------------------------------------------------- best lineup
@pytest.mark.parametrize("mix", SLOT_MIXES)
def test_fast_lineup_matches_the_exact_optimizer(mix: str) -> None:
    """The greedy matroid method must equal the Hungarian optimizer on random rosters."""
    slots = SLOT_MIXES[mix]
    rng = random.Random(mix)
    for _ in range(150):
        players = [
            LineupPlayer(i, rng.choice(["QB", "RB", "RB", "WR", "WR", "TE", "K", "DEF"]),
                         round(rng.uniform(0, 30), 1), "BN")
            for i in range(rng.randint(3, 18))
        ]  # fmt: skip
        exact = optimal_lineup(slots, players).optimal_points
        fast = best_lineup_points(starting_slots(slots), [(p.position, p.points) for p in players])
        assert fast == pytest.approx(exact, abs=0.011), (mix, players)


def test_lineup_ignores_negative_and_unusable_players() -> None:
    slots = starting_slots(["QB", "WR", "BN"])
    assert best_lineup_points(slots, [("QB", -3.0), ("TE", 40.0), ("WR", 10.0)]) == 10.0


def test_roster_limit_excludes_ir_and_taxi() -> None:
    assert roster_limit(SLOT_MIXES["ir and taxi"]) == 9
    assert roster_limit(STANDARD) == 13


# --------------------------------------------------------------------------- team value
def test_bench_player_only_counts_in_the_week_he_would_start() -> None:
    slots = starting_slots(["WR", "BN"])
    starter = vp(1, "WR", 15, 0, 15)  # bye in week 2
    backup = vp(2, "WR", 8, 8, 8)
    weights = {1: 1.0, 2: 1.0, 3: 1.0}
    assert team_value(slots, [starter], weights) == 30
    assert team_value(slots, [starter, backup], weights) == 38  # backup only fills week 2


def test_weights_scale_weeks() -> None:
    slots = starting_slots(["RB"])
    assert team_value(slots, [vp(1, "RB", 10, 10)], {1: 1.0, 2: 1.5}) == 25


def test_taxi_players_cannot_start() -> None:
    slots = starting_slots(["RB"])
    assert team_value(slots, [vp(1, "RB", 20, can_start=False)], ONE_WEEK) == 0


def test_fit_to_limit_drops_the_cheapest() -> None:
    slots = starting_slots(["RB", "RB", "BN"])
    roster = [vp(1, "RB", 20), vp(2, "RB", 15), vp(3, "RB", 5), vp(4, "RB", 1)]
    kept, dropped = fit_to_limit(slots, roster, 3, ONE_WEEK)
    assert [p.player_id for p in dropped] == [4]
    assert len(kept) == 3


def test_fit_to_limit_ignores_ir_players() -> None:
    slots = starting_slots(["RB", "BN"])
    roster = [vp(1, "RB", 20), vp(2, "RB", 0, counts_toward_limit=False), vp(3, "RB", 5)]
    kept, dropped = fit_to_limit(slots, roster, 2, ONE_WEEK)
    assert dropped == [] and len(kept) == 3


# --------------------------------------------------------------------------- waivers
def roster_of_ten() -> list[ValuePlayer]:
    return [
        vp(1, "QB", 20), vp(2, "RB", 15), vp(3, "RB", 12), vp(4, "WR", 14), vp(5, "WR", 11),
        vp(6, "TE", 8), vp(7, "RB", 9), vp(8, "K", 7), vp(9, "DEF", 6), vp(10, "WR", 3),
    ]  # fmt: skip


def test_waivers_open_spot_needs_no_drop() -> None:
    slots = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF", "BN", "BN"]
    roster = roster_of_ten()
    out = waiver_gains(starting_slots(slots), roster, [vp(50, "WR", 13)], ONE_WEEK, 11)
    # 13-point WR replaces the 9-point RB in FLEX
    assert out[0].gain == pytest.approx(4.0) and out[0].drop_id is None


def test_waivers_full_roster_suggests_the_cheapest_drop() -> None:
    slots = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF", "BN"]
    roster = roster_of_ten()
    out = waiver_gains(starting_slots(slots), roster, [vp(50, "TE", 12)], ONE_WEEK, 10)
    assert out[0].gain == pytest.approx(4.0)  # 12-point TE over the 8-point TE
    assert out[0].drop_id == 10  # the 3-point WR on the bench costs nothing


def test_waivers_rank_best_first_and_skip_useless_players() -> None:
    slots = starting_slots(["QB", "RB", "WR", "BN"])
    roster = [vp(1, "QB", 20), vp(2, "RB", 10), vp(3, "WR", 10)]
    candidates = [vp(50, "RB", 9), vp(51, "WR", 18), vp(52, "RB", 14), vp(53, "K", 30)]
    out = waiver_gains(slots, roster, candidates, ONE_WEEK, 4)
    assert [(r.player_id, r.gain) for r in out] == [(51, 8.0), (52, 4.0), (50, 0.0), (53, 0.0)]


def test_waivers_rest_of_season_values_bye_cover() -> None:
    """A backup who covers a starter's bye is worth that week's points."""
    slots = starting_slots(["TE", "BN"])
    roster = [vp(1, "TE", 12, 0, 12)]
    out = waiver_gains(slots, roster, [vp(50, "TE", 6, 6, 6)], {1: 1.0, 2: 1.0, 3: 1.0}, 2)
    assert out[0].gain == pytest.approx(6.0)


# --------------------------------------------------------------------------- trades
def test_two_for_one_only_counts_the_second_player_if_he_starts() -> None:
    """ADR-048's example: a star WR for two good RBs."""
    slots = ["QB", "RB", "RB", "WR", "WR", "FLEX", "BN"]
    a = [vp(1, "QB", 20), vp(2, "RB", 14), vp(3, "RB", 13), vp(4, "WR", 25), vp(5, "WR", 10),
         vp(6, "WR", 9), vp(7, "RB", 4)]  # fmt: skip
    b = [vp(11, "QB", 18), vp(12, "RB", 16), vp(13, "RB", 15), vp(14, "WR", 11),
         vp(15, "WR", 10), vp(16, "RB", 9), vp(17, "TE", 2)]  # fmt: skip
    me, them = trade_impact(
        starting_slots(slots), a, b, {4}, {12, 13}, ONE_WEEK, roster_limit(slots)
    )
    # Team A: loses the 25-pt WR; RBs 16 and 15 start, 14 moves to FLEX, 13 to the bench.
    assert me.before == 20 + 14 + 13 + 25 + 10 + 9  # FLEX = best of WR 9 / RB 4 -> WR 9
    assert me.after == 20 + 16 + 15 + 10 + 9 + 14
    assert me.change == pytest.approx(-7.0)
    # Team A is one over the limit and drops its cheapest player (the 4-point RB).
    assert me.dropped == [7]
    # Team B before: QB 18, RB 16 + 15, WR 11 + 10, FLEX RB 9 = 79.
    # After: only one RB left (9), so a RB slot stays empty: QB 18, RB 9, WR 25 + 11,
    # FLEX WR 10 = 73. Two good RBs for one star can hurt the side that gets the star.
    assert (them.before, them.after) == (79, 73)
    assert them.dropped == []


def test_trade_impact_is_symmetric_in_who_is_a_and_b() -> None:
    slots = starting_slots(["QB", "RB", "WR", "BN"])
    a = [vp(1, "QB", 20), vp(2, "RB", 14), vp(3, "WR", 8)]
    b = [vp(11, "QB", 18), vp(12, "RB", 6), vp(13, "WR", 16)]
    ab = trade_impact(slots, a, b, {2}, {13}, ONE_WEEK, 4)
    ba = trade_impact(slots, b, a, {13}, {2}, ONE_WEEK, 4)
    assert (ab[0].change, ab[1].change) == (ba[1].change, ba[0].change)


def test_suggestions_help_me_and_respect_the_other_teams_loss_limit() -> None:
    slots = ["QB", "RB", "RB", "WR", "WR", "BN", "BN"]
    mine = [vp(1, "QB", 20), vp(2, "QB", 17), vp(3, "RB", 14), vp(4, "RB", 13),
            vp(5, "WR", 7), vp(6, "WR", 6), vp(7, "RB", 12)]  # fmt: skip
    theirs = [vp(11, "QB", 12), vp(12, "RB", 8), vp(13, "RB", 7), vp(14, "WR", 15),
              vp(15, "WR", 14), vp(16, "WR", 13), vp(17, "TE", 1)]  # fmt: skip
    ideas = suggest_trades(
        starting_slots(slots), mine, {99: theirs}, ONE_WEEK, roster_limit(slots), max_loss=0.0
    )
    assert ideas, "my spare QB and RB for their spare WR should be found"
    for idea in ideas:
        assert idea.my_change > 0 and idea.their_change >= 0
    best = ideas[0]
    assert set(best.gets) <= {14, 15, 16}

    looser = suggest_trades(
        starting_slots(slots), mine, {99: theirs}, ONE_WEEK, roster_limit(slots), max_loss=5.0
    )
    assert len(looser) >= len(ideas)
    assert all(i.their_change >= -5.0 for i in looser)
