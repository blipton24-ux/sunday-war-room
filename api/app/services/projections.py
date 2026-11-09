"""Compute, store and freeze projections for a league's players (worker side).

Integrity rules (Projection Model spec):
* Frozen at kickoff: a row is only written while the player's game hasn't started; at kickoff
  it is marked frozen and never changes again.
* Rows are shared by every league with the same scoring_key, and carry model_version.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from sqlalchemy import and_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import League, NflGame, Player, Projection, RosterEntry, Team
from app.logging import get_logger
from app.model.distribution import load_calibration
from app.model.projection import MODEL_VERSION, Context, project_week
from app.model.scoring import scoring_key
from app.services.history import load_stat_rows, scored_history

log = get_logger("projections")


@dataclass(frozen=True)
class GameInfo:
    opponent: str
    kickoff_at: datetime | None
    home: bool


async def week_games(db: AsyncSession, season: int, week: int) -> dict[str, GameInfo]:
    """team -> its game this week. A team missing from the map is on bye."""
    games = await db.scalars(select(NflGame).where(NflGame.season == season, NflGame.week == week))
    out: dict[str, GameInfo] = {}
    for g in games:
        out[g.home] = GameInfo(g.away, g.kickoff_at, True)
        out[g.away] = GameInfo(g.home, g.kickoff_at, False)
    return out


def has_kicked_off(game: GameInfo | None, now: datetime) -> bool:
    return game is not None and game.kickoff_at is not None and game.kickoff_at <= now


def history_id(p: Player) -> str:
    """The id used to look up a player's history. No nflverse link = no history (prior)."""
    return p.gsis_id or f"sleeper:{p.sleeper_id}"


async def league_player_ids(db: AsyncSession, league_id: int, week: int) -> set[int]:
    rows = await db.scalars(
        select(RosterEntry.player_id)
        .join(Team, Team.id == RosterEntry.team_id)
        .where(Team.league_id == league_id, RosterEntry.week == week)
    )
    return set(rows)


async def compute_projections(
    db: AsyncSession, league: League, week: int, *, now: datetime | None = None
) -> dict[str, int]:
    """Project every player rostered in `league` for `week`; freeze any whose game started."""
    now = now or datetime.now(UTC)
    key = league.scoring_key or scoring_key(league.scoring_rules)
    season = league.season
    player_ids = await league_player_ids(db, league.id, week)
    if not player_ids:
        return {"computed": 0, "frozen": 0}

    players = (await db.scalars(select(Player).where(Player.id.in_(player_ids)))).all()
    games = await week_games(db, season, week)
    frozen_ids = set(
        await db.scalars(
            select(Projection.player_id).where(
                Projection.player_id.in_(player_ids),
                Projection.season == season,
                Projection.week == week,
                Projection.scoring_key == key,
                Projection.model_version == MODEL_VERSION,
                Projection.frozen.is_(True),
            )
        )
    )
    to_compute = [
        p for p in players
        if p.id not in frozen_ids and not has_kicked_off(games.get(p.nfl_team or ""), now)
    ]  # fmt: skip

    if to_compute:
        stat_rows = await load_stat_rows(db, [season - 1, season])
        history = scored_history(stat_rows, league.scoring_rules)
        targets = pd.DataFrame(
            [
                {
                    "player_id": p.id,
                    "gsis_id": history_id(p),
                    "position": p.position,
                    "team": p.nfl_team,
                    "opponent": g.opponent if (g := games.get(p.nfl_team or "")) else None,
                    "injury_status": p.injury_status,
                    "depth_chart_order": p.depth_chart_order,
                }
                for p in to_compute
            ]
        )
        result = project_week(
            history, targets, Context(season, week), load_calibration(MODEL_VERSION)
        )
        await _upsert(db, result, season, week, key, now)

    # Freeze everything whose game has started (including rows computed in an earlier run).
    started = [p.id for p in players if has_kicked_off(games.get(p.nfl_team or ""), now)]
    frozen = 0
    if started:
        res = await db.execute(
            update(Projection)
            .where(
                Projection.player_id.in_(started),
                Projection.season == season,
                Projection.week == week,
                Projection.scoring_key == key,
                Projection.frozen.is_(False),
            )
            .values(frozen=True)
        )
        frozen = res.rowcount or 0  # type: ignore[attr-defined]
    await db.commit()
    log.info("projections_computed", league_id=league.id, week=week, computed=len(to_compute),
             newly_frozen=frozen)  # fmt: skip
    return {"computed": len(to_compute), "frozen": frozen}


async def _upsert(
    db: AsyncSession, result: pd.DataFrame, season: int, week: int, key: str, now: datetime
) -> None:
    rows: list[dict[str, Any]] = [
        {
            "player_id": int(r["player_id"]),
            "season": season,
            "week": week,
            "scoring_key": key,
            "points": float(r["points"]),
            "p10": float(r["p10"]),
            "p50": float(r["p50"]),
            "p90": float(r["p90"]),
            "factors": r["factors"],
            "model_version": MODEL_VERSION,
            "computed_at": now,
            "frozen": False,
        }
        for r in result.to_dict("records")
    ]
    for i in range(0, len(rows), 1000):
        stmt = insert(Projection).values(rows[i : i + 1000])
        ex = stmt.excluded
        await db.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    Projection.player_id, Projection.season, Projection.week,
                    Projection.scoring_key, Projection.model_version,
                ],
                set_={k: getattr(ex, k) for k in ("points", "p10", "p50", "p90", "factors",
                                                   "computed_at")},
                where=and_(Projection.frozen.is_(False)),  # never touch a frozen row
            )
        )  # fmt: skip
