from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_db
from db.models import Theme
from db.schemas import ThemeCreate, ThemeOut

router = APIRouter()


@router.get("/", response_model=list[ThemeOut])
async def list_themes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Theme).order_by(Theme.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=ThemeOut, status_code=201)
async def create_theme(payload: ThemeCreate, db: AsyncSession = Depends(get_db)):
    theme = Theme(**payload.model_dump())
    db.add(theme)
    await db.flush()
    await db.refresh(theme)
    return theme


@router.get("/{theme_id}", response_model=ThemeOut)
async def get_theme(theme_id: int, db: AsyncSession = Depends(get_db)):
    theme = await db.get(Theme, theme_id)
    if not theme:
        raise HTTPException(404, "Thème introuvable")
    return theme


@router.patch("/{theme_id}", response_model=ThemeOut)
async def update_theme(theme_id: int, payload: ThemeCreate, db: AsyncSession = Depends(get_db)):
    theme = await db.get(Theme, theme_id)
    if not theme:
        raise HTTPException(404, "Thème introuvable")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(theme, k, v)
    await db.flush()
    await db.refresh(theme)
    return theme


@router.delete("/{theme_id}", status_code=204)
async def delete_theme(theme_id: int, db: AsyncSession = Depends(get_db)):
    theme = await db.get(Theme, theme_id)
    if not theme:
        raise HTTPException(404, "Thème introuvable")
    await db.delete(theme)

