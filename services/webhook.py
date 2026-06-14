import httpx


async def send_discord(webhook_url: str, content: str, theme_name: str) -> bool:
    """Envoie le digest sur Discord via webhook."""
    payload = {
        "username": "Vigil",
        "embeds": [
            {
                "title": f"Digest — {theme_name}",
                "description": content[:4000],
                "color": 0x5865F2,
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(webhook_url, json=payload, timeout=10)
        return response.status_code == 204


async def send_discord_article(webhook_url: str, article_id: int, title: str, url: str, summary: str, score: float, theme_name: str, app_id: str) -> bool:
    """Envoie un article individuel avec boutons de feedback."""
    score_bar = "🟢" if score >= 7 else "🟡" if score >= 4 else "🔴"
    payload = {
        "username": "Vigil",
        "embeds": [
            {
                "title": title[:256],
                "url": url,
                "description": f"{summary}\n\n**Score:** {score_bar} `{score}/10` — **Theme:** {theme_name}",
                "color": 0x5865F2,
            }
        ],
        "components": [
            {
                "type": 1,  # Action row
                "components": [
                    {
                        "type": 2,  # Button
                        "style": 3,  # Green
                        "label": "Relevant",
                        "emoji": {"name": "👍"},
                        "custom_id": f"feedback_like_{article_id}",
                    },
                    {
                        "type": 2,
                        "style": 4,  # Red
                        "label": "Not relevant",
                        "emoji": {"name": "👎"},
                        "custom_id": f"feedback_dislike_{article_id}",
                    },
                    {
                        "type": 2,
                        "style": 5,  # Link
                        "label": "Read article",
                        "url": url,
                    }
                ]
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(webhook_url, json=payload, timeout=10)
        return response.status_code == 204