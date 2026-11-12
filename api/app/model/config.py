"""Switches for the projection model (P4, ADR-054).

Every idea being tested is one field here, off by default. `SHIPPED` is what live code runs, so
it only changes in the same commit that bumps MODEL_VERSION. The backtest builds a candidate
from the shipped config plus one switch and compares the two. Names in `CANDIDATES` are what
`python -m app.scripts.backtest --compare shipped,<name>` accepts.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class ModelConfig:
    # Leave games where the player was hurt out of his own history when projecting later weeks
    # (needs the `injury_game` column on the history frame; see features/injury_games.py).
    skip_injury_games_in_history: bool = False


SHIPPED = ModelConfig()

CANDIDATES: dict[str, ModelConfig] = {
    "shipped": SHIPPED,
    "skip-injury-history": replace(SHIPPED, skip_injury_games_in_history=True),
}


def by_name(name: str) -> ModelConfig:
    try:
        return CANDIDATES[name]
    except KeyError:
        raise SystemExit(f"Unknown model config {name!r}. Known: {', '.join(CANDIDATES)}") from None
