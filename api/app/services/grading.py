"""Grade frozen projections against what actually happened (feeds the Accuracy page).

A projection is graded once its game is final (nflverse has the final score). `genuine` is
true only if it was computed before kickoff; the Accuracy page counts genuine rows only.
A player with no stat row in a final game scored 0 (didn't play or recorded nothing).
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import League, NflGame, Player, PlayerWeekStats, Projection, ProjectionGrade
from app.logging import get_logger
from app.model.scoring import score

log = get_logger("grading")


async def grade_finished(db: AsyncSession, season: int) -> int:
    """Grade every ungraded projection in `season` whose game is final. Idempotent."""
    pending = (
        await db.execute(
            select(Projection, Player)
            .join(Player, Player.id == Projection.player_id)
            .outerjoin(ProjectionGrade, ProjectionGrade.projection_id == Projection.id)
            .where(Projection.season == season, ProjectionGrade.projection_id.is_(None))
        )
    ).all()
    if not pending:
        return 0

    games = (await db.scalars(select(NflGame).where(NflGame.season == season))).all()
    final = {}
    for g in games:
        if g.home_score is not None and g.away_score is not None:
            final[(g.week, g.home)] = g.kickoff_at
            final[(g.week, g.away)] = g.kickoff_at

    rules_by_key = {
        k: r
        for k, r in (await db.execute(select(League.scoring_key, League.scoring_rules))).all()
        if k
    }
    stats = {
        (s.gsis_id, s.week): s
        for s in await db.scalars(select(PlayerWeekStats).where(PlayerWeekStats.season == season))
    }

    grades = []
    for proj, player in pending:
        row = stats.get((player.gsis_id or "", proj.week))
        # The team the player was on that week (trades!), else their current team.
        team = row.team if row is not None and row.team else (player.nfl_team or "")
        kickoff = final.get((proj.week, team))
        rules = rules_by_key.get(proj.scoring_key)
        if kickoff is None or rules is None:
            continue  # game not final yet (or bye), or no league uses this scoring any more
        if row is None:
            actual = 0.0
        else:
            frame = pd.DataFrame([{**row.stats, "position": row.position}])
            actual = float(score(frame, rules).iloc[0])
        grades.append(
            {
                "projection_id": proj.id,
                "actual_points": actual,
                "genuine": proj.computed_at < kickoff,
            }
        )
    if grades:
        await db.execute(insert(ProjectionGrade).values(grades).on_conflict_do_nothing())
        await db.commit()
    log.info("graded", season=season, graded=len(grades))
    return len(grades)
