"""Following leagues, choosing "my team", and refreshing (docs/Specs/API.md)."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.auth.deps import DB, CurrentUser, Membership
from app.config import Settings, get_settings
from app.db.models import League, LeagueMembership, SyncRun, Team
from app.errors import ApiError, NotFound
from app.jobs.tracking import create_run
from app.queue import Queue, get_queue
from app.schemas import (
    FollowLeagueIn,
    FollowLeagueOut,
    JobAccepted,
    LeagueOut,
    SetMyTeamIn,
    TeamOut,
)

router = APIRouter(prefix="/api/v1/leagues", tags=["leagues"])
QueueDep = Annotated[Queue, Depends(get_queue)]
ACTIVE = ("queued", "running")


async def _latest_sync_status(db: DB, league_id: int) -> str | None:
    return await db.scalar(
        select(SyncRun.status)
        .where(SyncRun.league_id == league_id, SyncRun.kind == "sync_league")
        .order_by(SyncRun.id.desc())
        .limit(1)
    )


async def _league_out(db: DB, league: League, membership: LeagueMembership) -> LeagueOut:
    return LeagueOut(
        id=league.id,
        platform=league.platform,
        external_id=league.external_id,
        season=league.season,
        name=league.name,
        avatar_url=league.avatar_url,
        current_week=league.current_week,
        my_team_id=membership.my_team_id,
        last_synced_at=league.last_synced_at,
        sync_status=await _latest_sync_status(db, league.id),
    )


async def _enqueue_sync(db: DB, queue: Queue, league_id: int, user_id: int | None) -> SyncRun:
    """Enqueue a sync, or return the one already queued/running (no duplicate work)."""
    active = await db.scalar(
        select(SyncRun).where(
            SyncRun.league_id == league_id,
            SyncRun.kind == "sync_league",
            SyncRun.status.in_(ACTIVE),
        )
    )
    if active is not None:
        return active
    run = await create_run(db, "sync_league", league_id=league_id, requested_by=user_id)
    await queue.enqueue_job("sync_league_job", run.id, league_id, _job_id=run.job_id)
    return run


@router.get("", response_model=list[LeagueOut])
async def list_leagues(user: CurrentUser, db: DB) -> list[LeagueOut]:
    rows = (
        await db.execute(
            select(LeagueMembership, League)
            .join(League, League.id == LeagueMembership.league_id)
            .where(LeagueMembership.user_id == user.id)
            .order_by(League.name)
        )
    ).all()
    return [await _league_out(db, lg, m) for m, lg in rows]


@router.post("", status_code=202, response_model=FollowLeagueOut)
async def follow_league(
    body: FollowLeagueIn, user: CurrentUser, db: DB, queue: QueueDep
) -> FollowLeagueOut:
    """Follow a league found by the user's latest Sleeper connect, then sync it."""
    connect = await db.scalar(
        select(SyncRun)
        .where(
            SyncRun.requested_by == user.id,
            SyncRun.kind == "sleeper_connect",
            SyncRun.status == "done",
        )
        .order_by(SyncRun.id.desc())
        .limit(1)
    )
    offered = {
        lg["external_id"]: lg
        for lg in ((connect.result or {}).get("leagues", []) if connect else [])
    }
    found = offered.get(body.external_id)
    if found is None:
        raise NotFound(
            "That league isn't in your connected Sleeper account", code="league_not_offered"
        )

    stmt = insert(League).values(
        platform=body.platform,
        external_id=body.external_id,
        season=int(found["season"]),
        name=str(found["name"]),
        scoring_rules={},
        roster_slots=[],
    )
    upsert = stmt.on_conflict_do_update(  # no-op update so RETURNING gives the existing id
        index_elements=[League.platform, League.external_id, League.season],
        set_={"external_id": stmt.excluded.external_id},
    ).returning(League.id)
    league_id = (await db.execute(upsert)).scalar_one()
    await db.execute(
        insert(LeagueMembership)
        .values(user_id=user.id, league_id=league_id)
        .on_conflict_do_nothing(index_elements=["user_id", "league_id"])
    )
    await db.commit()

    run = await _enqueue_sync(db, queue, league_id, user.id)
    league = await db.get(League, league_id)
    membership = await db.scalar(
        select(LeagueMembership).where(
            LeagueMembership.user_id == user.id, LeagueMembership.league_id == league_id
        )
    )
    assert league is not None and membership is not None and run.job_id is not None
    return FollowLeagueOut(league=await _league_out(db, league, membership), job_id=run.job_id)


@router.get("/{league_id}/teams", response_model=list[TeamOut])
async def list_teams(membership: Membership, db: DB) -> list[TeamOut]:
    """Teams in a league (for choosing "my team")."""
    teams = await db.scalars(
        select(Team).where(Team.league_id == membership.league_id).order_by(Team.name)
    )
    return [TeamOut.model_validate(t) for t in teams]


@router.patch("/{league_id}", response_model=LeagueOut)
async def set_my_team(body: SetMyTeamIn, membership: Membership, db: DB) -> LeagueOut:
    team = await db.get(Team, body.my_team_id)
    if team is None or team.league_id != membership.league_id:
        raise ApiError(422, "invalid_team", "That team isn't in this league")
    membership.my_team_id = team.id
    await db.commit()
    league = await db.get(League, membership.league_id)
    assert league is not None
    return await _league_out(db, league, membership)


@router.delete("/{league_id}", status_code=204)
async def unfollow_league(membership: Membership, db: DB) -> Response:
    await db.execute(delete(LeagueMembership).where(LeagueMembership.id == membership.id))
    await db.commit()
    return Response(status_code=204)


@router.post("/{league_id}/refresh", status_code=202, response_model=JobAccepted)
async def refresh_league(
    membership: Membership,
    user: CurrentUser,
    db: DB,
    queue: QueueDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> JobAccepted:
    """Queue a sync now. Returns the running job if one is already in flight.

    Rate limited per user per league (REFRESH_MIN_INTERVAL_SECONDS).
    """
    window = datetime.now(UTC) - timedelta(seconds=settings.refresh_min_interval_seconds)
    recent = await db.scalar(
        select(SyncRun.id).where(
            SyncRun.league_id == membership.league_id,
            SyncRun.kind == "sync_league",
            SyncRun.requested_by == user.id,
            SyncRun.status.not_in(ACTIVE),
            SyncRun.created_at > window,
        )
    )
    if recent is not None:
        raise ApiError(429, "rate_limited", "Refreshed moments ago, try again in a minute")
    run = await _enqueue_sync(db, queue, membership.league_id, user.id)
    assert run.job_id is not None
    return JobAccepted(job_id=run.job_id, status=run.status)
