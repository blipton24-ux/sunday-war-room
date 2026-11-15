"""Opportunity signals: a player's share of his team's targets and carries.

Kept from the first P4 approach as a reference for P4 step 4: the signals here move into the
feature table (`app/model/ml/features.py`) and this file is deleted then.

Needs raw stat columns on the history frame (`scored_history(..., keep=...)`).
"""

from __future__ import annotations

import pandas as pd


def usage_share(history: pd.DataFrame) -> pd.Series:
    """A player's share of his team's targets and carries in each game."""
    opps = history["targets"] + history["carries"]
    team = opps.groupby([history["team"], history["season"], history["week"]]).transform("sum")
    return (opps / team.where(team > 0)).where(history["position"].isin(["RB", "WR", "TE"]))
