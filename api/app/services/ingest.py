"""nflverse -> PostgreSQL (ADR-030): bulk, idempotent loads. Called from worker jobs only.

A season reload replaces that season's rows in one transaction, so readers never see a
half-loaded season and re-running is always safe.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import polars as pl
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import NflGame, Player, PlayerWeekStats
from app.logging import get_logger
from app.nfl_teams import defense_key
from app.sources import nflverse

log = get_logger("ingest")
BATCH = 2000
KEY_COLS = {"gsis_id", "name", "position", "season", "week", "season_type", "team", "opponent"}


@dataclass(frozen=True)
class NflverseFrames:
    """Everything one ingest needs, loaded up front (network + parsing happen here)."""

    schedule: pl.DataFrame
    player_stats: pl.DataFrame
    defense_stats: pl.DataFrame
    snaps: pl.DataFrame
    ids: pl.DataFrame


def fetch_frames(seasons: Sequence[int]) -> NflverseFrames:
    """Blocking (downloads). Run in a thread from async code."""
    ids = nflverse.load_id_crosswalk()
    schedule = nflverse.load_schedule(seasons)
    return NflverseFrames(
        schedule=schedule,
        player_stats=nflverse.load_player_stats(seasons),
        defense_stats=nflverse.load_defense_stats(seasons, schedule),
        snaps=nflverse.load_snap_shares(seasons, ids),
        ids=ids,
    )


async def _bulk_insert(db: AsyncSession, model: Any, rows: list[dict[str, Any]]) -> None:
    for i in range(0, len(rows), BATCH):
        await db.execute(insert(model).values(rows[i : i + BATCH]))


async def upsert_games(db: AsyncSession, schedule: pl.DataFrame) -> int:
    rows = schedule.to_dicts()
    for i in range(0, len(rows), BATCH):
        stmt = insert(NflGame).values(rows[i : i + BATCH])
        ex = stmt.excluded
        await db.execute(
            stmt.on_conflict_do_update(
                index_elements=[NflGame.game_id],
                set_={
                    "kickoff_at": ex.kickoff_at,
                    "home_score": ex.home_score,
                    "away_score": ex.away_score,
                    "home": ex.home,
                    "away": ex.away,
                    "week": ex.week,
                },
            )
        )
    return len(rows)


def stats_rows(frames: NflverseFrames) -> list[dict[str, Any]]:
    """One dict per player-week: key columns + a compact `stats` map (zeros omitted)."""
    snaps = frames.snaps.rename({"offense_pct": "offense_snap_pct"})
    out: list[dict[str, Any]] = []
    for frame in (frames.player_stats, frames.defense_stats):
        joined = frame.join(snaps, on=["gsis_id", "season", "week"], how="left")
        for rec in joined.iter_rows(named=True):
            stats = {
                k: float(v)
                for k, v in rec.items()
                if k not in KEY_COLS and k != "offense_snap_pct" and v
            }
            out.append(
                {
                    "gsis_id": rec["gsis_id"],
                    "season": rec["season"],
                    "week": rec["week"],
                    "season_type": rec["season_type"],
                    "position": rec["position"],
                    "team": rec["team"],
                    "opponent": rec["opponent"],
                    "stats": stats,
                    "offense_snap_pct": rec.get("offense_snap_pct"),
                }
            )
    # One row per key even if upstream ever duplicates one (e.g. a mid-week trade glitch).
    dedup = {(r["gsis_id"], r["season"], r["week"]): r for r in out}
    if len(dedup) != len(out):
        log.warning("duplicate_player_weeks", dropped=len(out) - len(dedup))
    return list(dedup.values())


async def replace_week_stats(db: AsyncSession, rows: list[dict[str, Any]]) -> int:
    seasons = sorted({r["season"] for r in rows})
    await db.execute(delete(PlayerWeekStats).where(PlayerWeekStats.season.in_(seasons)))
    await _bulk_insert(db, PlayerWeekStats, rows)
    return len(rows)


async def apply_crosswalk(db: AsyncSession, ids: pl.DataFrame) -> int:
    """Set players.gsis_id from nflverse's sleeper_id mapping; team defenses get TEAM_<abbr>.

    gsis_id is unique, so an id that moved to a different Sleeper player is first cleared.
    """
    mapping = {
        r["sleeper_id"]: r["gsis_id"]
        for r in ids.filter(pl.col("sleeper_id").is_not_null()).iter_rows(named=True)
    }
    rows = await db.execute(select(Player.id, Player.sleeper_id, Player.position, Player.gsis_id))
    changes: dict[int, str] = {}
    for pid, sid, pos, current in rows:
        if sid is None:
            continue
        target = defense_key(sid) if pos == "DEF" else mapping.get(sid)
        if target is not None and target != current:
            changes[pid] = target
    if not changes:
        return 0
    ids_changing = list(changes)
    # Free every gsis id about to be (re)claimed, including by its current holder, so the
    # unique constraint can't trip mid-update; then write all new links in one batch.
    await db.execute(
        update(Player)
        .where(Player.gsis_id.in_(set(changes.values())) | Player.id.in_(ids_changing))
        .values(gsis_id=None)
    )
    await db.execute(update(Player), [{"id": pid, "gsis_id": g} for pid, g in changes.items()])
    return len(changes)


async def ingest_nflverse(db: AsyncSession, seasons: Sequence[int]) -> dict[str, int]:
    frames = await asyncio.to_thread(fetch_frames, seasons)
    games = await upsert_games(db, frames.schedule)
    stats = await replace_week_stats(db, stats_rows(frames))
    linked = await apply_crosswalk(db, frames.ids)
    await db.commit()
    result = {"games": games, "player_weeks": stats, "players_linked": linked}
    log.info("nflverse_ingested", seasons=list(seasons), **result)
    return result
