from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from db.session import get_db
from db.models import Theme
from db.schemas import ThemeCreate, ThemeOut
from api.login_helpers import get_current_user_id

router = APIRouter()


async def _get_theme_or_404(theme_id: int, user_id: uuid.UUID, db: AsyncSession) -> Theme:
    theme = await db.get(Theme, theme_id)
    if not theme or theme.user_id != user_id:
        raise HTTPException(404, "Theme not found")
    return theme


@router.get("/", response_model=list[ThemeOut])
async def list_themes(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    result = await db.execute(
        select(Theme)
        .where(Theme.user_id == user_id)
        .order_by(Theme.created_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=ThemeOut, status_code=201)
async def create_theme(
    payload: ThemeCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    theme = Theme(**payload.model_dump(), user_id=user_id)
    db.add(theme)
    await db.flush()
    await db.refresh(theme)
    return theme


@router.get("/{theme_id}", response_model=ThemeOut)
async def get_theme(
    theme_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    return await _get_theme_or_404(theme_id, user_id, db)


@router.patch("/{theme_id}", response_model=ThemeOut)
async def update_theme(
    theme_id: int,
    payload: ThemeCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    theme = await _get_theme_or_404(theme_id, user_id, db)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(theme, k, v)
    await db.flush()
    await db.refresh(theme)
    return theme


@router.delete("/{theme_id}", status_code=204)
async def delete_theme(
    theme_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    theme = await _get_theme_or_404(theme_id, user_id, db)
    await db.delete(theme)