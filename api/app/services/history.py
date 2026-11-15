"""Load scored player history from Postgres for the model (one set-based query, ADR-030)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    DepthChartWeek,
    InjuryReport,
    NflGame,
    PlayerBackground,
    PlayerWeekStats,
)
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
            InjuryReport.practice_status,
        ).where(InjuryReport.season.in_(list(seasons)))
    )
    return pd.DataFrame(
        rows.all(),
        columns=["gsis_id", "season", "week", "report_status", "roster_status", "practice_status"],
    )


async def load_depth_rows(db: AsyncSession, seasons: Sequence[int]) -> pd.DataFrame:
    """Depth-chart tier per player-week (1 starter, 2 next in line, 3 deeper)."""
    rows = await db.execute(
        select(
            DepthChartWeek.gsis_id, DepthChartWeek.season, DepthChartWeek.week,
            DepthChartWeek.depth_tier,
        ).where(DepthChartWeek.season.in_(list(seasons)))
    )  # fmt: skip
    return pd.DataFrame(rows.all(), columns=["gsis_id", "season", "week", "depth_tier"])


async def load_background_rows(db: AsyncSession) -> pd.DataFrame:
    """Birth date, rookie season and draft round and pick for every stored player."""
    rows = await db.execute(
        select(
            PlayerBackground.gsis_id, PlayerBackground.birth_date, PlayerBackground.rookie_season,
            PlayerBackground.draft_round, PlayerBackground.draft_pick,
        )
    )  # fmt: skip
    return pd.DataFrame(
        rows.all(), columns=["gsis_id", "birth_date", "rookie_season", "draft_round", "draft_pick"]
    )


async def load_game_rows(db: AsyncSession, seasons: Sequence[int]) -> pd.DataFrame:
    """Stored regular-season games with scores and betting lines (game context for the P4 model)."""
    rows = await db.execute(
        select(
            NflGame.season, NflGame.week, NflGame.home, NflGame.away, NflGame.spread_line,
            NflGame.total_line, NflGame.home_score, NflGame.away_score, NflGame.kickoff_at,
            NflGame.roof,
        ).where(NflGame.season.in_(list(seasons)), NflGame.game_type == "REG")
    )  # fmt: skip
    return pd.DataFrame(
        rows.all(),
        columns=["season", "week", "home", "away", "spread_line", "total_line", "home_score",
                 "away_score", "kickoff_at", "roof"],
    )  # fmt: skip


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
