from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from db.session import get_db
from db.models import Webhook, Theme
from db.schemas import WebhookCreate, WebhookOut
from api.login_helpers import get_current_user_id

router = APIRouter()


async def _get_webhook_or_404(webhook_id: int, user_id: uuid.UUID, db: AsyncSession) -> Webhook:
    webhook = await db.get(Webhook, webhook_id)
    if not webhook or webhook.user_id != user_id:
        raise HTTPException(404, "Webhook not found")
    return webhook


@router.get("/", response_model=list[WebhookOut])
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    result = await db.execute(
        select(Webhook).where(Webhook.user_id == user_id)
    )
    return result.scalars().all()


@router.post("/", response_model=WebhookOut, status_code=201)
async def create_webhook(
    payload: WebhookCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    # Vérifier que le thème cible appartient à l'user
    theme = await db.get(Theme, payload.theme_id)
    if not theme or theme.user_id != user_id:
        raise HTTPException(403, "Theme not found or access denied")

    webhook = Webhook(**payload.model_dump(), user_id=user_id)
    db.add(webhook)
    await db.flush()
    await db.refresh(webhook)
    return webhook


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    webhook = await _get_webhook_or_404(webhook_id, user_id, db)
    await db.delete(webhook)