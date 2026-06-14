from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.session import get_db
from db.models import Article
from db.schemas import ArticleOut

router = APIRouter()


@router.get("/", response_model=list[ArticleOut])
async def list_articles(
    theme_id: int | None = None,
    min_score: float | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Article)
        .options(selectinload(Article.analysis))
        .order_by(Article.fetched_at.desc())
        .limit(limit)
    )
    if theme_id:
        query = query.join(Article.source).where(Article.source.has(theme_id=theme_id))
    if min_score is not None:
        query = query.join(Article.analysis).where(Article.analysis.has(relevance_score=min_score))

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{article_id}", response_model=ArticleOut)
async def get_article(article_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Article)
        .options(selectinload(Article.analysis))
        .where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article introuvable")
    return article


@router.post("/{article_id}/process")
async def trigger_processing(article_id: int, db: AsyncSession = Depends(get_db)):
    """Déclenche manuellement l''analyse LLM d''un article."""
    from workers.tasks import process_article
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "Article introuvable")
    process_article.delay(article_id)
    return {"message": f"Traitement lancé pour l''article {article_id}"}

