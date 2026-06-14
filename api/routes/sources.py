from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_db
from db.models import Source
from db.schemas import SourceCreate, SourceOut

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
    source = Source(**payload.model_dump())
    db.add(source)
    await db.flush()
    await db.refresh(source)
    return source


@router.get("/{source_id}", response_model=SourceOut)
async def get_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source introuvable")
    return source


@router.patch("/{source_id}", response_model=SourceOut)
async def update_source(source_id: int, payload: SourceCreate, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source introuvable")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(source, k, v)
    await db.flush()
    await db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=204)
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source introuvable")
    await db.delete(source)


@router.post("/{source_id}/toggle", response_model=SourceOut)
async def toggle_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source introuvable")
    source.active = not source.active
    await db.flush()
    await db.refresh(source)
    return source

