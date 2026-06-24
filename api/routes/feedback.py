from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from db.session import get_db
from db.models import Feedback, Article
from db.schemas import FeedbackCreate, FeedbackOut
from api.login_helpers import get_current_user_id

router = APIRouter()


@router.post("/", response_model=FeedbackOut, status_code=201)
async def create_feedback(
    payload: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    article = await db.get(Article, payload.article_id)
    if not article:
        raise HTTPException(404, "Article not found")
    if payload.rating not in (-1, 1):
        raise HTTPException(400, "Rating must be 1 (👍) or -1 (👎)")

    # Upsert : un seul feedback par user/article
    result = await db.execute(
        select(Feedback).where(
            Feedback.user_id == user_id,
            Feedback.article_id == payload.article_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.rating = payload.rating
        if payload.comment is not None:
            existing.comment = payload.comment
        await db.flush()
        await db.refresh(existing)
        return existing

    feedback = Feedback(**payload.model_dump(), user_id=user_id)
    db.add(feedback)
    await db.flush()
    await db.refresh(feedback)
    return feedback


@router.get("/article/{article_id}", response_model=list[FeedbackOut])
async def get_article_feedbacks(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    result = await db.execute(
        select(Feedback)
        .where(Feedback.article_id == article_id, Feedback.user_id == user_id)
        .order_by(Feedback.created_at.desc())
    )
    return result.scalars().all()