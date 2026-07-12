from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select

from db.session import AsyncSessionLocal
from db.models_projects import TrackedRepo, RepoEvent
from services.github import verify_github_signature, parse_event
from config import settings

router = APIRouter()


@router.post("/")
async def github_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not verify_github_signature(settings.github_webhook_secret, body, signature):
        raise HTTPException(401, "Invalid signature")

    event_type = request.headers.get("X-GitHub-Event", "")
    payload = await request.json()

    # PING envoyé par GitHub à la création du webhook
    if event_type == "ping":
        return {"status": "pong"}

    parsed = parse_event(event_type, payload)
    if not parsed:
        return {"status": "ignored"}

    github_repo_id = payload.get("repository", {}).get("id")

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TrackedRepo).where(TrackedRepo.github_repo_id == github_repo_id)
        )
        repo = result.scalar_one_or_none()
        if not repo or not repo.active:
            return {"status": "repo not tracked"}

        event = RepoEvent(tracked_repo_id=repo.id, **parsed)
        db.add(event)
        await db.flush()
        event_id = event.id
        await db.commit()

    # Réponse rapide à GitHub (<10s), le reste part en tâches async
    from workers.tasks_projects import sync_notion_task, send_discord_event
    sync_notion_task.delay(event_id)
    send_discord_event.delay(event_id)

    return {"status": "recorded", "event_id": event_id}

