"""Waiver rules in our terms (ADR-046/047). Pure.

* Status: a player dropped less than `clear_days` ago is on waivers until that time is up;
  everyone else is a free agent (add now). Platforms differ in exactly when waivers run, so
  the time is shown as "about"; Verification Gaps V-33 tracks checking it on a real league.
* FAAB bid guide: a share of the budget left that grows with the points per week the player
  adds to your best lineup, capped, and never below the league's minimum bid. A guide only:
  what others bid can't be known.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any, Literal

WaiverState = Literal["free_agent", "waivers"]

BID_SHARE_PER_POINT = 0.05  # each projected point per week added is worth 5% of what's left
MAX_BID_SHARE = 0.6
BID_SPREAD = 0.25  # the range is +-25% around the middle


def waiver_status(
    dropped_at: datetime | None, rules: Mapping[str, Any], now: datetime
) -> tuple[WaiverState, datetime | None]:
    """("waivers", until) for a recently dropped player, else ("free_agent", None)."""
    clear_days = int(rules.get("clear_days") or 0)
    if rules.get("kind") == "none" or dropped_at is None or clear_days <= 0:
        return "free_agent", None
    until = dropped_at + timedelta(days=clear_days)
    return ("waivers", until) if now < until else ("free_agent", None)


def faab_bid(gain_per_week: float, remaining: int, min_bid: int = 0) -> tuple[int, int] | None:
    """Suggested (low, high) bid, or None when there's nothing to bid or nothing gained."""
    if remaining <= 0 or gain_per_week <= 0:
        return None
    middle = remaining * min(MAX_BID_SHARE, gain_per_week * BID_SHARE_PER_POINT)
    low = max(min_bid, math.floor(middle * (1 - BID_SPREAD)))
    high = max(low, math.ceil(middle * (1 + BID_SPREAD)))
    return min(low, remaining), min(high, remaining)
