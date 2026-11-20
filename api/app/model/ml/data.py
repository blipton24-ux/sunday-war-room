"""Everything the feature table reads, loaded from PostgreSQL in one place (ADR-030).

The same `ModelData` serves the backtest (every season from 2016) and the live weekly compute
(the current season and the ones before it), so both build features from the same frames.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.history import (
    load_background_rows,
    load_depth_rows,
    load_game_rows,
    load_injury_rows,
    load_stat_rows,
)


@dataclass(frozen=True)
class ModelData:
    """`stats`: one row per player-game, raw stat columns (load_stat_rows).
    `games`: regular-season games with lines, scores, kickoff and roof.
    `injuries`: weekly report and reserve-list rows. `depth`: tier per player-week.
    `background`: one row per player (birth date, rookie season, draft round and pick)."""

    stats: pd.DataFrame
    games: pd.DataFrame
    injuries: pd.DataFrame
    depth: pd.DataFrame
    background: pd.DataFrame


async def load_model_data(db: AsyncSession, seasons: Sequence[int]) -> ModelData:
    return ModelData(
        stats=await load_stat_rows(db, seasons),
        games=await load_game_rows(db, seasons),
        injuries=await load_injury_rows(db, seasons),
        depth=await load_depth_rows(db, seasons),
        background=await load_background_rows(db),
    )
