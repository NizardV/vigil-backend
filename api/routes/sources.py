from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from db.session import get_db
from db.models import Source, Theme
from db.schemas import SourceCreate, SourceOut
from services.source_detector import detect_source_type, validate_rss_url
from api.login_helpers import get_current_user_id

router = APIRouter()


async def _get_source_or_404(source_id: int, user_id: uuid.UUID, db: AsyncSession) -> Source:
    """Récupère une source et vérifie que le thème parent appartient à l'user."""
    result = await db.execute(
        select(Source)
        .join(Theme, Source.theme_id == Theme.id)
        .where(Source.id == source_id, Theme.user_id == user_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(404, "Source not found")
    return source


@router.get("/", response_model=list[SourceOut])
async def list_sources(
    theme_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    query = (
        select(Source)
        .join(Theme, Source.theme_id == Theme.id)
        .where(Theme.user_id == user_id)
    )
    if theme_id:
        query = query.where(Source.theme_id == theme_id)
    result = await db.execute(query.order_by(Source.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=SourceOut, status_code=201)
async def create_source(
    payload: SourceCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    # Vérifier que le thème cible appartient bien à l'user
    theme = await db.get(Theme, payload.theme_id)
    if not theme or theme.user_id != user_id:
        raise HTTPException(403, "Theme not found or access denied")

    source_type, rss_url = detect_source_type(payload.url)
    is_valid = await validate_rss_url(rss_url)
    if not is_valid:
        raise HTTPException(400, f"Could not reach the RSS feed at {rss_url}. Please check the URL.")

    source = Source(
        name=payload.name,
        url=rss_url,
        theme_id=payload.theme_id,
        type=source_type,
        active=payload.active,
        fetch_interval_hours=payload.fetch_interval_hours,
    )
    db.add(source)
    await db.flush()
    await db.refresh(source)
    return source


@router.get("/{source_id}", response_model=SourceOut)
async def get_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    return await _get_source_or_404(source_id, user_id, db)


@router.patch("/{source_id}", response_model=SourceOut)
async def update_source(
    source_id: int,
    payload: SourceCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    source = await _get_source_or_404(source_id, user_id, db)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(source, k, v)
    await db.flush()
    await db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=204)
async def delete_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    source = await _get_source_or_404(source_id, user_id, db)
    await db.delete(source)


@router.post("/{source_id}/toggle", response_model=SourceOut)
async def toggle_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    source = await _get_source_or_404(source_id, user_id, db)
    source.active = not source.active
    await db.flush()
    await db.refresh(source)
    return source