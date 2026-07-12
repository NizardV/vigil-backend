import hashlib
import hmac
import httpx

from config import settings

GITHUB_API = "https://api.github.com"


def verify_github_signature(secret: str, body: bytes, signature_header: str | None) -> bool:
    """Vérifie le header X-Hub-Signature-256 envoyé par GitHub."""
    if not secret or not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)


async def list_user_repos() -> list[dict]:
    """Liste tous les repos (publics + privés) possédés par le compte du PAT configuré."""
    repos: list[dict] = []
    page = 1
    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(
                f"{GITHUB_API}/user/repos",
                headers=_headers(),
                params={"per_page": 100, "page": page, "affiliation": "owner"},
                timeout=15,
            )
            response.raise_for_status()
            batch = response.json()
            if not batch:
                break
            repos.extend(batch)
            page += 1
    return repos


async def ensure_webhook(owner: str, repo: str, callback_url: str) -> int | None:
    """Crée le webhook GitHub sur le repo s'il n'existe pas déjà. Retourne son id."""
    async with httpx.AsyncClient() as client:
        existing = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/hooks",
            headers=_headers(),
            timeout=15,
        )
        if existing.status_code == 200:
            for hook in existing.json():
                if hook.get("config", {}).get("url") == callback_url:
                    return hook["id"]
        elif existing.status_code == 404:
            # Pas les droits admin sur ce repo (ex: repo d'un ancien projet de groupe)
            return None

        response = await client.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/hooks",
            headers=_headers(),
            json={
                "name": "web",
                "active": True,
                "events": ["push", "pull_request", "issues", "release"],
                "config": {
                    "url": callback_url,
                    "content_type": "json",
                    "secret": settings.github_webhook_secret,
                },
            },
            timeout=15,
        )
        if response.status_code == 201:
            return response.json()["id"]
        return None


def parse_event(event_type: str, payload: dict) -> dict | None:
    """Extrait un résumé exploitable d'un event GitHub. Retourne None si pas significatif."""
    if event_type == "push":
        commits = payload.get("commits", [])
        if not commits:
            return None
        branch = payload.get("ref", "").removeprefix("refs/heads/")
        head = commits[-1]
        first_line = (head.get("message", "") or "").splitlines()[0][:120] if head.get("message") else ""
        return {
            "event_type": "push",
            "github_ref": (head.get("id") or "")[:7],
            "actor": payload.get("pusher", {}).get("name"),
            "summary": f"{len(commits)} commit(s) sur `{branch}` — {first_line}",
            "url": head.get("url"),
        }

    if event_type == "pull_request":
        action = payload.get("action")
        pr = payload.get("pull_request", {})
        merged = pr.get("merged", False)

        if action == "opened":
            label = "PR ouverte"
        elif action == "closed" and merged:
            label = "PR mergée"
        else:
            return None  # fermée sans merge, review, etc. : pas significatif

        return {
            "event_type": "pull_request",
            "github_ref": f"#{pr.get('number')}",
            "actor": pr.get("user", {}).get("login"),
            "summary": f"{label} — {(pr.get('title') or '')[:120]}",
            "url": pr.get("html_url"),
        }

    if event_type == "issues":
        if payload.get("action") != "closed":
            return None
        issue = payload.get("issue", {})
        return {
            "event_type": "issues",
            "github_ref": f"#{issue.get('number')}",
            "actor": payload.get("sender", {}).get("login"),
            "summary": f"Issue fermée — {(issue.get('title') or '')[:120]}",
            "url": issue.get("html_url"),
        }

    if event_type == "release":
        if payload.get("action") != "published":
            return None
        release = payload.get("release", {})
        return {
            "event_type": "release",
            "github_ref": release.get("tag_name"),
            "actor": (release.get("author") or {}).get("login"),
            "summary": f"Release publiée — {release.get('name') or release.get('tag_name')}",
            "url": release.get("html_url"),
        }

    return None


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

