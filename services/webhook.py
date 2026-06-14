import httpx


async def send_discord(webhook_url: str, content: str, theme_name: str) -> bool:
    """Envoie un message sur Discord via webhook."""
    payload = {
        "username": "Vigil",
        "embeds": [
            {
                "title": f"📡 Digest — {theme_name}",
                "description": content[:4000],  # limite Discord
                "color": 0x5865F2,  # bleu Discord
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(webhook_url, json=payload, timeout=10)
        return response.status_code == 204

