import httpx

DISCORD_API = "https://discord.com/api/v10"


async def _get_channel_id(bot_token: str, webhook_url: str) -> str | None:
    """Récupère le channel_id depuis le webhook."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            webhook_url,
            headers={"Authorization": f"Bot {bot_token}"}
        )
        if response.status_code == 200:
            return response.json().get("channel_id")
    return None


async def send_discord(webhook_url: str, content: str, theme_name: str, bot_token: str = "") -> bool:
    """Envoie le digest sur Discord."""
    payload = {
        "embeds": [
            {
                "title": f"Digest — {theme_name}",
                "description": content[:4000],
                "color": 0x5865F2,
            }
        ]
    }

    if bot_token:
        channel_id = await _get_channel_id(bot_token, webhook_url)
        if channel_id:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{DISCORD_API}/channels/{channel_id}/messages",
                    json=payload,
                    headers={"Authorization": f"Bot {bot_token}"},
                    timeout=10,
                )
                return response.status_code == 200

    # Fallback webhook classique (sans boutons)
    async with httpx.AsyncClient() as client:
        payload["username"] = "Vigil"
        response = await client.post(webhook_url, json=payload, timeout=10)
        return response.status_code == 204


async def send_discord_article(webhook_url: str, article_id: int, title: str, url: str, summary: str, score: float, theme_name: str, bot_token: str = "") -> bool:
    """Envoie un article individuel avec boutons de feedback."""
    score_bar = "🟢" if score >= 7 else "🟡" if score >= 4 else "🔴"
    payload = {
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
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 3,
                        "label": "Relevant",
                        "emoji": {"name": "👍"},
                        "custom_id": f"feedback_like_{article_id}",
                    },
                    {
                        "type": 2,
                        "style": 4,
                        "label": "Not relevant",
                        "emoji": {"name": "👎"},
                        "custom_id": f"feedback_dislike_{article_id}",
                    },
                    {
                        "type": 2,
                        "style": 5,
                        "label": "Read article",
                        "url": url,
                    }
                ]
            }
        ]
    }

    if bot_token:
        channel_id = await _get_channel_id(bot_token, webhook_url)
        if channel_id:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{DISCORD_API}/channels/{channel_id}/messages",
                    json=payload,
                    headers={"Authorization": f"Bot {bot_token}"},
                    timeout=10,
                )
                return response.status_code == 200

    # Fallback sans boutons
    payload.pop("components", None)
    payload["username"] = "Vigil"
    async with httpx.AsyncClient() as client:
        response = await client.post(webhook_url, json=payload, timeout=10)
        return response.status_code == 204