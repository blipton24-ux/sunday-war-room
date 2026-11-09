from fastapi import APIRouter
from sqlalchemy import select

from app.auth.deps import DB, CurrentUser
from app.db.models import LeagueMembership, SyncRun
from app.errors import NotFound, error_responses
from app.schemas import JobOut

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"], responses=error_responses())


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: str, user: CurrentUser, db: DB) -> JobOut:
    """Status of a background job. Visible to whoever asked for it, or to members of its league."""
    run = await db.scalar(select(SyncRun).where(SyncRun.job_id == job_id))
    visible = run is not None and (
        run.requested_by == user.id
        or (
            run.league_id is not None
            and await db.scalar(
                select(LeagueMembership.id).where(
                    LeagueMembership.user_id == user.id,
                    LeagueMembership.league_id == run.league_id,
                )
            )
            is not None
        )
    )
    if run is None or not visible:
        raise NotFound("Job not found", code="job_not_found")
    assert run.job_id is not None
    return JobOut(
        job_id=run.job_id,
        kind=run.kind,
        status=run.status,
        league_id=run.league_id,
        error=run.error if run.status == "failed" else None,
        result=run.result,
        created_at=run.created_at,
        finished_at=run.finished_at,
    )
