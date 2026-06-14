from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_db
from db.models import Digest, Webhook
from db.schemas import DigestOut, WebhookCreate, WebhookOut

# ── Digests ──────────────────────────────────────────────

router = APIRouter()


@router.get("/", response_model=list[DigestOut])
async def list_digests(theme_id: int | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Digest).order_by(Digest.sent_at.desc()).limit(20)
    if theme_id:
        query = query.where(Digest.theme_id == theme_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/trigger/{theme_id}")
async def trigger_digest(theme_id: int, db: AsyncSession = Depends(get_db)):
    """Déclenche manuellement la génération et l''envoi du digest."""
    from workers.tasks import send_digest
    send_digest.delay(theme_id)
    return {"message": f"Digest lancé pour le thème {theme_id}"}

