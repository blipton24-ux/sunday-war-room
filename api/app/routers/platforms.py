from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.deps import DB, CurrentUser
from app.errors import error_responses
from app.jobs.tracking import create_run
from app.queue import Queue, get_queue
from app.schemas import JobAccepted, SleeperConnectIn

router = APIRouter(prefix="/api/v1/platforms", tags=["platforms"], responses=error_responses())


@router.post("/sleeper/connect", status_code=202, response_model=JobAccepted)
async def connect_sleeper(
    body: SleeperConnectIn,
    user: CurrentUser,
    db: DB,
    queue: Annotated[Queue, Depends(get_queue)],
) -> JobAccepted:
    """Look up a Sleeper username and its leagues for the current season.

    Runs in the worker (the API never calls Sleeper during a request). Poll
    GET /api/v1/jobs/{job_id}; when done, `result.leagues` lists what can be followed.
    """
    run = await create_run(db, "sleeper_connect", requested_by=user.id)
    await queue.enqueue_job("connect_sleeper", run.id, user.id, body.username, _job_id=run.job_id)
    assert run.job_id is not None
    return JobAccepted(job_id=run.job_id, status=run.status)
