from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_db
from db.models import Feedback, Article
from db.schemas import FeedbackCreate, FeedbackOut

router = APIRouter()


@router.post("/", response_model=FeedbackOut, status_code=201)
async def create_feedback(payload: FeedbackCreate, db: AsyncSession = Depends(get_db)):
    article = await db.get(Article, payload.article_id)
    if not article:
        raise HTTPException(404, "Article introuvable")
    if payload.rating not in (-1, 1):
        raise HTTPException(400, "Rating doit être 1 (👍) ou -1 (👎)")

    feedback = Feedback(**payload.model_dump())
    db.add(feedback)
    await db.flush()
    await db.refresh(feedback)
    return feedback


@router.get("/article/{article_id}", response_model=list[FeedbackOut])
async def get_article_feedbacks(article_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Feedback)
        .where(Feedback.article_id == article_id)
        .order_by(Feedback.created_at.desc())
    )
    return result.scalars().all()

