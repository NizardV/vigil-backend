import hashlib
import hmac
import json
import time

from fastapi import APIRouter, Request, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import AsyncSessionLocal
from db.models import Feedback
from config import settings

router = APIRouter()


def verify_discord_signature(public_key: str, timestamp: str, body: bytes, signature: str) -> bool:
    """Vérifie la signature Discord pour sécuriser les interactions."""
    try:
        from nacl.signing import VerifyKey
        from nacl.exceptions import BadSignatureError
        verify_key = VerifyKey(bytes.fromhex(public_key))
        verify_key.verify(f"{timestamp}{body.decode()}".encode(), bytes.fromhex(signature))
        return True
    except Exception:
        return False


@router.post("/interactions")
async def discord_interactions(request: Request):
    """Point d'entrée pour les interactions Discord (boutons)."""

    # Vérification de la signature Discord (obligatoire)
    signature = request.headers.get("X-Signature-Ed25519", "")
    timestamp = request.headers.get("X-Signature-Timestamp", "")
    body = await request.body()

    if not verify_discord_signature(settings.discord_public_key, timestamp, body, signature):
        raise HTTPException(status_code=401, detail="Invalid request signature")

    data = json.loads(body)
    interaction_type = data.get("type")

    # Type 1 = PING (Discord vérifie l'URL lors de la configuration)
    if interaction_type == 1:
        return {"type": 1}

    # Type 3 = MESSAGE_COMPONENT (bouton cliqué)
    if interaction_type == 3:
        custom_id = data["data"]["custom_id"]
        user = data["member"]["user"] if "member" in data else data.get("user", {})
        username = user.get("username", "unknown")

        # Parse le custom_id : feedback_like_123 ou feedback_dislike_123
        if custom_id.startswith("feedback_like_"):
            article_id = int(custom_id.replace("feedback_like_", ""))
            rating = 1
            label = "Relevant"
        elif custom_id.startswith("feedback_dislike_"):
            article_id = int(custom_id.replace("feedback_dislike_", ""))
            rating = -1
            label = "Not relevant"
        else:
            return {"type": 4, "data": {"content": "Unknown action.", "flags": 64}}

        # Sauvegarde en BDD
        async with AsyncSessionLocal() as db:
            feedback = Feedback(
                article_id=article_id,
                rating=rating,
                comment=f"Discord feedback by {username}",
            )
            db.add(feedback)
            await db.commit()

        # Réponse éphémère (visible seulement par l'utilisateur qui a cliqué)
        emoji = "👍" if rating == 1 else "👎"
        return {
            "type": 4,
            "data": {
                "content": f"{emoji} Feedback **{label}** recorded. Thank you!",
                "flags": 64  # Ephemeral
            }
        }

    return {"type": 1}