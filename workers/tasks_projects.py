from datetime import datetime

from celery.schedules import crontab
from sqlalchemy import select

from workers.tasks import app, run_async
from config import settings
from db.session import AsyncSessionLocal
from db.models_projects import TrackedRepo, RepoEvent
from services import github, notion
from services.webhook import send_discord

# ── Planification ────────────────────────────────────────
# Seul polling qui reste : découverte quotidienne des nouveaux repos
# et création des webhooks manquants (le reste est event-driven).

app.conf.beat_schedule["discover-repos-daily"] = {
    "task": "workers.tasks_projects.discover_repos",
    "schedule": crontab(hour=4, minute=0),
}


# ── Tâche : découverte des repos + création des webhooks ──

@app.task(name="workers.tasks_projects.discover_repos")
def discover_repos():
    async def _run():
        repos = await github.list_user_repos()
        callback_url = f"{settings.app_url}/api/github-webhooks/"

        async with AsyncSessionLocal() as db:
            for repo_data in repos:
                result = await db.execute(
                    select(TrackedRepo).where(TrackedRepo.github_repo_id == repo_data["id"])
                )
                repo = result.scalar_one_or_none()

                if not repo:
                    repo = TrackedRepo(
                        github_repo_id=repo_data["id"],
                        full_name=repo_data["full_name"],
                        private=repo_data["private"],
                    )
                    db.add(repo)
                    await db.flush()

                if not repo.webhook_id and repo.active:
                    owner, name = repo_data["full_name"].split("/", 1)
                    repo.webhook_id = await github.ensure_webhook(owner, name, callback_url)

                repo.last_synced_at = datetime.utcnow()

            await db.commit()

    run_async(_run())


# ── Tâche : sync Notion suite à un event ───────────────────

@app.task(name="workers.tasks_projects.sync_notion_task", bind=True, max_retries=3)
def sync_notion_task(self, event_id: int):
    async def _run():
        async with AsyncSessionLocal() as db:
            event = await db.get(RepoEvent, event_id)
            if not event:
                return
            repo = await db.get(TrackedRepo, event.tracked_repo_id)
            if not repo:
                return

            if not repo.notion_page_id:
                repo.notion_page_id = await notion.find_or_create_project_page(repo.full_name)

            if repo.notion_page_id:
                count_result = await db.execute(
                    select(RepoEvent).where(RepoEvent.tracked_repo_id == repo.id)
                )
                event_count = len(count_result.scalars().all())
                ok = await notion.sync_repo_activity(repo.notion_page_id, event.summary, event_count)
                if ok:
                    event.notion_synced_at = datetime.utcnow()

            await db.commit()

    try:
        run_async(_run())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


# ── Tâche : digest Discord event-driven ────────────────────

@app.task(name="workers.tasks_projects.send_discord_event")
def send_discord_event(event_id: int):
    async def _run():
        async with AsyncSessionLocal() as db:
            event = await db.get(RepoEvent, event_id)
            if not event or not settings.discord_projects_webhook_url:
                return
            repo = await db.get(TrackedRepo, event.tracked_repo_id)
            if not repo:
                return

            content = f"**{repo.full_name}** — {event.summary}"
            if event.url:
                content += f"\n{event.url}"

            ok = await send_discord(
                settings.discord_projects_webhook_url,
                content,
                repo.full_name,
                bot_token=settings.discord_bot_token,
            )
            if ok:
                event.discord_sent_at = datetime.utcnow()
            await db.commit()

    run_async(_run())

