from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select

from app.adapters.espn import make_credentials, parse_league_link
from app.auth.deps import DB, CurrentUser
from app.db.models import LeagueMembership, PlatformAccount
from app.errors import ApiError, error_responses
from app.jobs.tracking import create_run
from app.queue import Queue, get_queue
from app.schemas import EspnCredentialsIn, EspnProbeIn, JobAccepted, SleeperConnectIn
from app.services.credentials import NEEDS_RECONNECT, save_espn_credentials

router = APIRouter(prefix="/api/v1/platforms", tags=["platforms"], responses=error_responses())
QueueDep = Annotated[Queue, Depends(get_queue)]


@router.post("/sleeper/connect", status_code=202, response_model=JobAccepted)
async def connect_sleeper(
    body: SleeperConnectIn,
    user: CurrentUser,
    db: DB,
    queue: QueueDep,
) -> JobAccepted:
    """Look up a Sleeper username and its leagues for the current season.

    Runs in the worker (the API never calls Sleeper during a request). Poll
    GET /api/v1/jobs/{job_id}; when done, `result.leagues` lists what can be followed.
    """
    run = await create_run(db, "sleeper_connect", requested_by=user.id)
    await queue.enqueue_job("connect_sleeper", run.id, user.id, body.username, _job_id=run.job_id)
    assert run.job_id is not None
    return JobAccepted(job_id=run.job_id, status=run.status)


@router.post("/espn/probe", status_code=202, response_model=JobAccepted)
async def probe_espn_league(
    body: EspnProbeIn, user: CurrentUser, db: DB, queue: QueueDep
) -> JobAccepted:
    """Is a pasted ESPN league public? (ADR-051: league link first.)

    Poll GET /api/v1/jobs/{job_id}. The result is one of: `public` (with `leagues` and `teams`),
    `private` (ask for the cookies), or `unsupported` (a league type we can't score yet).
    """
    try:
        link = parse_league_link(body.link)
    except ValueError as exc:
        raise ApiError(422, "invalid_league_link", str(exc)) from exc
    run = await create_run(db, "espn_probe", requested_by=user.id)
    await queue.enqueue_job(
        "probe_espn", run.id, user.id, link.league_id, link.season, _job_id=run.job_id
    )
    assert run.job_id is not None
    return JobAccepted(job_id=run.job_id, status=run.status)


@router.post("/espn/credentials", status_code=202, response_model=JobAccepted)
async def connect_espn(
    body: EspnCredentialsIn, user: CurrentUser, db: DB, queue: QueueDep
) -> JobAccepted:
    """Save the user's ESPN cookies (encrypted) and list their leagues (ADR-051, ADR-052).

    The cookies are stored here and only the account id is queued, because job arguments are kept
    unencrypted in Redis. Poll GET /api/v1/jobs/{job_id}; when done, `result.leagues` lists the
    user's ESPN leagues, each with `team_id` (the user's own team). The cookies are never returned
    by any endpoint.
    """
    try:
        creds = make_credentials(body.espn_s2.get_secret_value(), body.swid.get_secret_value())
    except ValueError as exc:
        raise ApiError(422, "invalid_cookies", str(exc)) from exc
    account = await save_espn_credentials(db, user.id, creds)
    run = await create_run(db, "espn_connect", requested_by=user.id)
    await queue.enqueue_job("connect_espn", run.id, user.id, account.id, _job_id=run.job_id)
    assert run.job_id is not None
    return JobAccepted(job_id=run.job_id, status=run.status)


@router.delete("/espn", status_code=204)
async def disconnect_espn(user: CurrentUser, db: DB) -> Response:
    """Forget the user's stored ESPN cookies.

    Leagues followed with those cookies stay followed but ask to reconnect; an account no league
    uses is removed outright.
    """
    account = await db.scalar(
        select(PlatformAccount).where(
            PlatformAccount.user_id == user.id, PlatformAccount.platform == "espn"
        )
    )
    if account is not None:
        in_use = await db.scalar(
            select(func.count())
            .select_from(LeagueMembership)
            .where(LeagueMembership.platform_account_id == account.id)
        )
        if in_use:
            account.credentials_encrypted = None
            account.status = NEEDS_RECONNECT
        else:
            await db.delete(account)
        await db.commit()
    return Response(status_code=204)
