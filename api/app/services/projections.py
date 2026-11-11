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
from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    League,
    NflGame,
    Player,
    PlayerWeekStats,
    Projection,
    RestOfSeasonProjection,
    RosterEntry,
    Team,
)
from app.logging import get_logger
from app.model.distribution import load_calibration
from app.model.projection import MODEL_VERSION, Context, project_week
from app.model.rest_of_season import Horizon, project_rest_of_season, season_horizon
from app.model.scoring import scoring_key
from app.services.history import load_stat_rows, scored_history

log = get_logger("projections")

# Rest-of-season rows carry the weekly model's version plus their own (rest_of_season.py).
ROS_MODEL_VERSION = f"{MODEL_VERSION}+ros1"
FANTASY_POSITIONS = ("QB", "RB", "WR", "TE", "K", "DEF")
POOL_DEPTH = 3  # free agents this deep on their team's depth chart are worth projecting


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
    return p.gsis_id or f"player:{p.id}"


async def league_player_ids(db: AsyncSession, league_id: int, week: int) -> set[int]:
    rows = await db.scalars(
        select(RosterEntry.player_id)
        .join(Team, Team.id == RosterEntry.team_id)
        .where(Team.league_id == league_id, RosterEntry.week == week)
    )
    return set(rows)


async def projection_pool(db: AsyncSession, league: League, week: int) -> set[int]:
    """Players worth projecting for a league: its rosters plus realistic free agents.

    A free agent counts if he is on an NFL team at a fantasy position and either played in
    this or last season, sits near the top of his depth chart, or is a kicker or defense.
    """
    rostered = await league_player_ids(db, league.id, week)
    recent = (
        select(PlayerWeekStats.gsis_id)
        .where(PlayerWeekStats.season.in_([league.season - 1, league.season]))
        .distinct()
    )
    free_agents = await db.scalars(
        select(Player.id).where(
            Player.nfl_team.is_not(None),
            Player.position.in_(FANTASY_POSITIONS),
            or_(
                Player.position.in_(("K", "DEF")),
                Player.gsis_id.in_(recent),
                Player.depth_chart_order <= POOL_DEPTH,
            ),
        )
    )
    return rostered | set(free_agents)


async def compute_projections(
    db: AsyncSession,
    league: League,
    week: int,
    *,
    now: datetime | None = None,
    player_ids: set[int] | None = None,
) -> dict[str, int]:
    """Project players for `week` (default: everyone rostered in `league`); freeze any whose
    game started."""
    now = now or datetime.now(UTC)
    key = league.scoring_key or scoring_key(league.scoring_rules)
    season = league.season
    if player_ids is None:
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


# --------------------------------------------------------------------------- rest of season
def league_horizon(league: League, from_week: int) -> Horizon:
    rules = league.season_rules or {}
    return season_horizon(
        from_week,
        rules.get("playoff_week_start"),
        rules.get("playoff_teams"),
        rules.get("playoff_round", "one_week"),
    )


def horizon_key(h: Horizon) -> str:
    """Leagues whose seasons end, and whose playoffs start, in the same weeks share rows."""
    last = h.weeks[-1] if h.weeks else 0
    return f"{last}:{min(h.playoff_weeks) if h.playoff_weeks else 0}"


async def season_schedule(
    db: AsyncSession, season: int, weeks: tuple[int, ...]
) -> dict[int, dict[str, str]]:
    """week -> {team: opponent} for the weeks whose games are loaded."""
    games = await db.scalars(
        select(NflGame).where(NflGame.season == season, NflGame.week.in_(list(weeks)))
    )
    out: dict[int, dict[str, str]] = {}
    for g in games:
        week = out.setdefault(g.week, {})
        week[g.home], week[g.away] = g.away, g.home
    return out


async def compute_rest_of_season(
    db: AsyncSession,
    league: League,
    from_week: int,
    player_ids: set[int],
    *,
    now: datetime | None = None,
) -> int:
    """Project `player_ids` over the rest of `league`'s fantasy season. Returns rows written."""
    now = now or datetime.now(UTC)
    horizon = league_horizon(league, from_week)
    if not horizon.weeks or not player_ids:
        return 0
    key = league.scoring_key or scoring_key(league.scoring_rules)
    hkey = horizon_key(horizon)
    season = league.season

    players = (await db.scalars(select(Player).where(Player.id.in_(player_ids)))).all()
    schedule = await season_schedule(db, season, horizon.weeks)
    history = scored_history(await load_stat_rows(db, [season - 1, season]), league.scoring_rules)
    targets = pd.DataFrame(
        [
            {
                "player_id": p.id,
                "gsis_id": history_id(p),
                "position": p.position,
                "team": p.nfl_team,
                "injury_status": p.injury_status,
                "depth_chart_order": p.depth_chart_order,
            }
            for p in players
        ]
    )
    result = project_rest_of_season(history, targets, season, horizon, schedule)

    # Older starting weeks for this scoring and season shape are no longer needed.
    await db.execute(
        delete(RestOfSeasonProjection).where(
            RestOfSeasonProjection.season == season,
            RestOfSeasonProjection.scoring_key == key,
            RestOfSeasonProjection.horizon_key == hkey,
            RestOfSeasonProjection.from_week < from_week,
        )
    )
    rows: list[dict[str, Any]] = [
        {
            "player_id": int(r["player_id"]),
            "season": season,
            "from_week": from_week,
            "scoring_key": key,
            "horizon_key": hkey,
            "points": float(r["ros_points"]),
            "games": int(r["games"]),
            "weekly": r["weekly"],
            "model_version": ROS_MODEL_VERSION,
            "computed_at": now,
        }
        for r in result.to_dict("records")
    ]
    for i in range(0, len(rows), 1000):
        stmt = insert(RestOfSeasonProjection).values(rows[i : i + 1000])
        ex = stmt.excluded
        await db.execute(
            stmt.on_conflict_do_update(
                constraint="uq_ros_projections_key",
                set_={k: getattr(ex, k) for k in ("points", "games", "weekly", "computed_at")},
            )
        )
    await db.commit()
    log.info("ros_computed", league_id=league.id, from_week=from_week, players=len(rows),
             horizon=hkey)  # fmt: skip
    return len(rows)
