"""Load scored player history from Postgres for the model (one set-based query, ADR-030)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import InjuryReport, PlayerWeekStats
from app.model.scoring import score


async def load_stat_rows(db: AsyncSession, seasons: Sequence[int]) -> pd.DataFrame:
    """Raw stat rows (one per player-game) with every stat as a column."""
    rows = await db.execute(
        select(
            PlayerWeekStats.gsis_id,
            PlayerWeekStats.season,
            PlayerWeekStats.week,
            PlayerWeekStats.position,
            PlayerWeekStats.team,
            PlayerWeekStats.opponent,
            PlayerWeekStats.offense_snap_pct,
            PlayerWeekStats.stats,
        ).where(PlayerWeekStats.season.in_(list(seasons)))
    )
    records = [
        {
            **stats,
            "gsis_id": gid,
            "season": season,
            "week": week,
            "position": pos,
            "team": team,
            "opponent": opp,
            "snap": snap,
        }
        for gid, season, week, pos, team, opp, snap, stats in rows
    ]
    return pd.DataFrame(records)


async def load_injury_rows(db: AsyncSession, seasons: Sequence[int]) -> pd.DataFrame:
    """Weekly injury designations and reserve-list status, for backtests."""
    rows = await db.execute(
        select(
            InjuryReport.gsis_id,
            InjuryReport.season,
            InjuryReport.week,
            InjuryReport.report_status,
            InjuryReport.roster_status,
        ).where(InjuryReport.season.in_(list(seasons)))
    )
    return pd.DataFrame(
        rows.all(), columns=["gsis_id", "season", "week", "report_status", "roster_status"]
    )


def scored_history(
    stat_rows: pd.DataFrame, rules: Mapping[str, float], keep: Sequence[str] = ()
) -> pd.DataFrame:
    """History in the model's shape: key columns + `points` under these scoring rules.

    `keep` names extra raw stat columns (targets, carries, ...) to carry along for the P4
    experiments; live code passes none, so its frame is unchanged."""
    if stat_rows.empty:
        return pd.DataFrame(
            columns=["gsis_id", "season", "week", "position", "team", "opponent", "points", "snap"]
        )
    out = stat_rows[["gsis_id", "season", "week", "position", "team", "opponent", "snap"]].copy()
    out["points"] = score(stat_rows, rules)
    for column in keep:
        out[column] = stat_rows[column].fillna(0.0) if column in stat_rows else 0.0
    return out
