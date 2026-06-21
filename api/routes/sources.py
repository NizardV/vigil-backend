from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_db
from db.models import Source
from db.schemas import SourceCreate, SourceOut
from services.source_detector import detect_source_type, validate_rss_url

router = APIRouter()


@router.get("/", response_model=list[SourceOut])
async def list_sources(theme_id: int | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Source)
    if theme_id:
        query = query.where(Source.theme_id == theme_id)
    result = await db.execute(query.order_by(Source.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=SourceOut, status_code=201)
async def create_source(payload: SourceCreate, db: AsyncSession = Depends(get_db)):
    # Détection automatique du type et conversion en URL RSS
    source_type, rss_url = detect_source_type(payload.url)

    # Validation que l'URL est accessible
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
async def get_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    return source


@router.patch("/{source_id}", response_model=SourceOut)
async def update_source(source_id: int, payload: SourceCreate, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(source, k, v)
    await db.flush()
    await db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=204)
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    await db.delete(source)


@router.post("/{source_id}/toggle", response_model=SourceOut)
async def toggle_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    source.active = not source.active
    await db.flush()
    await db.refresh(source)
    return source