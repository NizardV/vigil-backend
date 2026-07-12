from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_db
from db.models_projects import TrackedRepo
from db.schemas_projects import TrackedRepoOut, TrackedRepoUpdate
from api.login_helpers import get_current_user_id

router = APIRouter()


@router.get("/", response_model=list[TrackedRepoOut])
async def list_repos(
    db: AsyncSession = Depends(get_db),
    _user_id=Depends(get_current_user_id),
):
    result = await db.execute(select(TrackedRepo).order_by(TrackedRepo.full_name))
    return result.scalars().all()


@router.post("/sync", status_code=202)
async def force_sync(
    _user_id=Depends(get_current_user_id),
):
    from workers.tasks_projects import discover_repos
    discover_repos.delay()
    return {"status": "sync triggered"}


@router.patch("/{repo_id}", response_model=TrackedRepoOut)
async def update_repo(
    repo_id: int,
    payload: TrackedRepoUpdate,
    db: AsyncSession = Depends(get_db),
    _user_id=Depends(get_current_user_id),
):
    repo = await db.get(TrackedRepo, repo_id)
    if not repo:
        raise HTTPException(404, "Repo not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(repo, field, value)
    await db.flush()
    await db.refresh(repo)
    return repo

