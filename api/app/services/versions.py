"""Which model version a screen shows (backlog M-01).

A model version bump must not make past weeks vanish. Every projection row carries the version
that made it, and a frozen row is never changed, so a screen picks, per player:

1. the frozen row, from whichever version froze it (the number the player saw at kickoff);
2. else the current version's row;
3. else the newest row of any version.

Grading (the Accuracy page) stays per version: projections from different versions are never
averaged together or subtracted (docs/Specs/Projection-Model.md, integrity rules).
"""

from __future__ import annotations

from collections.abc import Iterable

from app.db.models import Projection
from app.model.projection import MODEL_VERSION

MIXED = "mixed"


def choose_projections(
    rows: Iterable[Projection], current: str = MODEL_VERSION
) -> dict[int, Projection]:
    """One projection per player: the frozen one, else the current version's, else the newest."""
    best: dict[int, tuple[tuple[int, float], Projection]] = {}
    for row in rows:
        rank = (
            2 if row.frozen else 1 if row.model_version == current else 0,
            row.computed_at.timestamp(),
        )
        held = best.get(row.player_id)
        if held is None or rank > held[0]:
            best[row.player_id] = (rank, row)
    return {pid: row for pid, (_, row) in best.items()}


def shown_version(rows: Iterable[Projection], current: str = MODEL_VERSION) -> str:
    """The version label for a screen: the one version shown, `mixed`, or the current one."""
    versions = {row.model_version for row in rows}
    if not versions:
        return current
    return versions.pop() if len(versions) == 1 else MIXED
