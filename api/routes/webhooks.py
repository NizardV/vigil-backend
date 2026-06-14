from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_db
from db.models import Webhook
from db.schemas import WebhookCreate, WebhookOut

router = APIRouter()


@router.get("/", response_model=list[WebhookOut])
async def list_webhooks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Webhook))
    return result.scalars().all()


@router.post("/", response_model=WebhookOut, status_code=201)
async def create_webhook(payload: WebhookCreate, db: AsyncSession = Depends(get_db)):
    webhook = Webhook(**payload.model_dump())
    db.add(webhook)
    await db.flush()
    await db.refresh(webhook)
    return webhook


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(webhook_id: int, db: AsyncSession = Depends(get_db)):
    webhook = await db.get(Webhook, webhook_id)
    if not webhook:
        raise HTTPException(404, "Webhook introuvable")
    await db.delete(webhook)

