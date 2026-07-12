import httpx

from config import settings

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


async def find_or_create_project_page(repo_full_name: str) -> str | None:
    """Cherche la page du repo dans la base Notion "project database" par son nom,
    la crée si elle n'existe pas.

    NOTE: suppose une propriété titre "Name" sur la base. À adapter si ton schéma
    Notion existant utilise un autre nom de propriété.
    """
    if not settings.notion_projects_db_id:
        return None

    async with httpx.AsyncClient() as client:
        search = await client.post(
            f"{NOTION_API}/databases/{settings.notion_projects_db_id}/query",
            headers=_headers(),
            json={"filter": {"property": "Name", "title": {"equals": repo_full_name}}},
            timeout=15,
        )
        if search.status_code != 200:
            return None
        results = search.json().get("results", [])
        if results:
            return results[0]["id"]

        created = await client.post(
            f"{NOTION_API}/pages",
            headers=_headers(),
            json={
                "parent": {"database_id": settings.notion_projects_db_id},
                "properties": {
                    "Name": {"title": [{"text": {"content": repo_full_name}}]},
                },
            },
            timeout=15,
        )
        if created.status_code == 200:
            return created.json()["id"]
        return None


async def sync_repo_activity(page_id: str, last_event_summary: str, event_count: int) -> bool:
    """Met à jour la page Notion du repo avec le dernier événement détecté.

    NOTE: suppose des propriétés "Last activity" (rich_text) et "Events tracked"
    (number) sur la base. À adapter à ton schéma Notion réel.
    """
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{NOTION_API}/pages/{page_id}",
            headers=_headers(),
            json={
                "properties": {
                    "Last activity": {"rich_text": [{"text": {"content": last_event_summary[:2000]}}]},
                    "Events tracked": {"number": event_count},
                }
            },
            timeout=15,
        )
        return response.status_code == 200


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.notion_api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

