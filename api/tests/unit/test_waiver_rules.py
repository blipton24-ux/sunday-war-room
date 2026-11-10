"""Waiver status and the FAAB bid guide (ADR-046/047)."""

from datetime import UTC, datetime, timedelta

import pytest

from app.model.waivers import MAX_BID_SHARE, faab_bid, waiver_status

NOW = datetime(2026, 11, 10, 12, tzinfo=UTC)


def test_never_dropped_is_a_free_agent() -> None:
    assert waiver_status(None, {"kind": "rolling", "clear_days": 2}, NOW) == ("free_agent", None)


def test_recent_drop_is_on_waivers_until_the_window_ends() -> None:
    dropped = NOW - timedelta(days=1)
    state, until = waiver_status(dropped, {"kind": "rolling", "clear_days": 2}, NOW)
    assert state == "waivers" and until == dropped + timedelta(days=2)


def test_window_over_means_free_agent() -> None:
    dropped = NOW - timedelta(days=3)
    assert waiver_status(dropped, {"kind": "faab", "clear_days": 2}, NOW)[0] == "free_agent"


@pytest.mark.parametrize("rules", [{"kind": "faab", "clear_days": 0}, {"kind": "none"}, {}])
def test_no_claim_window_means_free_agent(rules: dict[str, object]) -> None:
    assert waiver_status(NOW, rules, NOW)[0] == "free_agent"


def test_bid_grows_with_value_and_stays_inside_the_budget() -> None:
    small, big = faab_bid(1.0, 60), faab_bid(6.0, 60)
    assert small is not None and big is not None
    assert small[1] < big[0]
    assert faab_bid(100.0, 60) == (int(60 * MAX_BID_SHARE * 0.75), 45)  # capped share
    assert all(0 <= b <= 60 for b in (*small, *big))


def test_bid_respects_the_minimum_and_has_nothing_to_offer_without_budget_or_value() -> None:
    assert faab_bid(0.1, 100, min_bid=1) == (1, 1)
    assert faab_bid(5.0, 0) is None
    assert faab_bid(0.0, 100) is None
