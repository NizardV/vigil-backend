import asyncio
import feedparser
import httpx
from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from config import settings
from db.session import AsyncSessionLocal
from db.models import Article, Analysis, Source, Theme, Digest, Webhook, Feedback
from services.llm import analyze_article, generate_digest
from services.embeddings import get_embedding
from services.webhook import send_discord, send_discord_article

# ── Setup Celery ──────────────────────────────────────────

app = Celery("vigil")
app.config_from_object({
    "broker_url": settings.celery_broker_url,
    "result_backend": settings.celery_result_backend,
    "task_serializer": "json",
    "accept_content": ["json"],
    "timezone": "Europe/Paris",
    "enable_utc": True,
})

# ── Tâches planifiées ─────────────────────────────────────

app.conf.beat_schedule = {
    # Vérifie toutes les heures quelles sources collecter
    "check-sources-every-hour": {
        "task": "workers.tasks.fetch_all_sources",
        "schedule": crontab(minute=0),
    },
    # Vérifie toutes les heures quels digests envoyer
    "check-digests-every-hour": {
        "task": "workers.tasks.send_all_digests",
        "schedule": crontab(minute=0),
    },
}


# ── Helper asyncio ────────────────────────────────────────

def run_async(coro):
    """Exécute une coroutine depuis un contexte synchrone Celery."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ── Tâche : collecte toutes les sources ──────────────────

@app.task(name="workers.tasks.fetch_all_sources")
def fetch_all_sources():
    async def _run():
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Source).where(Source.active == True)
            )
            sources = result.scalars().all()

        for source in sources:
            # Vérifie si l'heure actuelle est un multiple de l'intervalle
            if now.hour % source.fetch_interval_hours == 0:
                fetch_source.delay(source.id)

    run_async(_run())


# ── Tâche : collecte une source RSS ──────────────────────

@app.task(name="workers.tasks.fetch_source")
def fetch_source(source_id: int):
    async def _run():
        async with AsyncSessionLocal() as db:
            source = await db.get(Source, source_id)
            if not source or not source.active:
                return

            feed = feedparser.parse(source.url)
            new_count = 0

            for entry in feed.entries[:20]:  # max 20 articles par source
                url = entry.get("link", "")
                title = entry.get("title", "Sans titre")
                content = entry.get("summary", entry.get("description", ""))

                # Dédoublonnage par URL
                existing = await db.execute(
                    select(Article).where(Article.url == url)
                )
                if existing.scalar_one_or_none():
                    continue

                article = Article(
                    source_id=source_id,
                    title=title,
                    url=url,
                    content_raw=content,
                    processed=False,
                )
                db.add(article)
                await db.flush()

                # Lance l''analyse en arrière-plan
                process_article.delay(article.id)
                new_count += 1

            await db.commit()
            return new_count

    return run_async(_run())


# ── Tâche : analyse LLM d''un article ─────────────────────

@app.task(name="workers.tasks.process_article", bind=True, max_retries=3)
def process_article(self, article_id: int):
    async def _run():
        async with AsyncSessionLocal() as db:
            # Récupère l''article avec sa source et son thème
            result = await db.execute(
                select(Article)
                .options(
                    selectinload(Article.source)
                    .selectinload(Source.theme)
                )
                .where(Article.id == article_id)
            )
            article = result.scalar_one_or_none()
            if not article or article.processed:
                return

            theme = article.source.theme

            # Contexte feedback pour personnaliser le prompt
            feedback_context = await _get_feedback_context(db, theme.id)

            # Appel LLM
            analysis_data = await analyze_article(
                title=article.title,
                content=article.content_raw or "",
                theme_name=theme.name,
                keywords=theme.keywords or [],
                feedback_context=feedback_context,
            )

            # Embedding pgvector
            text_for_embedding = f"{article.title} {analysis_data['summary']}"
            embedding = get_embedding(text_for_embedding)

            # Sauvegarde analyse
            analysis = Analysis(
                article_id=article.id,
                embedding=embedding,
                **analysis_data,
            )
            db.add(analysis)
            article.processed = True
            await db.commit()

    try:
        run_async(_run())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


# ── Tâche : digest quotidien tous les thèmes ─────────────

@app.task(name="workers.tasks.send_all_digests")
def send_all_digests():
    async def _run():
        from datetime import datetime
        current_hour = datetime.utcnow().hour
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Theme).where(
                    Theme.digest_enabled == True,
                    Theme.digest_hour == current_hour
                )
            )
            themes = result.scalars().all()
        for theme in themes:
            send_digest.delay(theme.id)

    run_async(_run())


# ── Tâche : digest pour un thème ─────────────────────────

@app.task(name="workers.tasks.send_digest")
def send_digest(theme_id: int):
    async def _run():
        async with AsyncSessionLocal() as db:
            theme = await db.get(Theme, theme_id)
            if not theme:
                return

            # Top 10 articles du jour par score
            result = await db.execute(
                select(Article, Analysis)
                .join(Analysis, Article.id == Analysis.article_id)
                .join(Source, Article.source_id == Source.id)
                .where(Source.theme_id == theme_id)
                .where(Article.processed == True)
                .where(Analysis.relevance_score >= 5.0)
                .order_by(Analysis.relevance_score.desc())
                .limit(10)
            )
            rows = result.all()

            if not rows:
                return

            articles_data = [
                {
                    "title": article.title,
                    "url": article.url,
                    "summary": analysis.summary,
                    "score": analysis.relevance_score,
                }
                for article, analysis in rows
            ]

            # Génère le digest
            digest_content = await generate_digest(articles_data, theme.name)

            # Sauvegarde en base
            digest = Digest(
                theme_id=theme_id,
                content=digest_content,
                channel="discord",
            )
            db.add(digest)

            # Envoie sur tous les webhooks actifs du thème
            webhooks_result = await db.execute(
                select(Webhook)
                .where(Webhook.theme_id == theme_id)
                .where(Webhook.active == True)
            )
            webhooks = webhooks_result.scalars().all()

            for webhook in webhooks:
                # 1. Envoie le digest global
                await send_discord(webhook.url, digest_content, theme.name, bot_token=settings.discord_bot_token)

                # 2. Envoie chaque article avec boutons de feedback
                for article, analysis in rows:
                    await send_discord_article(
                        webhook_url=webhook.url,
                        article_id=article.id,
                        title=article.title,
                        url=article.url,
                        summary=analysis.summary or "",
                        score=analysis.relevance_score or 0,
                        theme_name=theme.name,
                        bot_token=settings.discord_bot_token,
                    )

            await db.commit()

    run_async(_run())

# ── Helper : contexte feedback ────────────────────────────

async def _get_feedback_context(db, theme_id: int) -> str:
    """Construit un contexte textuel à partir des derniers feedbacks."""
    result = await db.execute(
        select(Feedback, Article)
        .join(Article, Feedback.article_id == Article.id)
        .join(Source, Article.source_id == Source.id)
        .where(Source.theme_id == theme_id)
        .order_by(Feedback.created_at.desc())
        .limit(10)
    )
    rows = result.all()

    if not rows:
        return ""

    liked = [a.title for f, a in rows if f.rating == 1]
    disliked = [a.title for f, a in rows if f.rating == -1]

    context = ""
    if liked:
        context += f"Articles apprecies : {', '.join(liked[:5])}\n"
    if disliked:
        context += f"Articles non pertinents : {', '.join(disliked[:5])}\n"

    return context

# ── Task : re-process pending articles ────────────────────────────

@app.task(name="workers.tasks.process_all_pending")
def process_all_pending():
    """Re-process all unprocessed articles."""
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Article).where(Article.processed == False)
            )
            articles = result.scalars().all()
            for article in articles:
                process_article.delay(article.id)
    run_async(_run())

from workers import tasks_projects # noqa: E402, F401
