import uuid
import json
from jose import jwt
import redis.asyncio as aioredis
from config import settings

SESSION_TTL = 30 * 24 * 60 * 60


def get_redis():
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def create_session(access_token: str, refresh_token: str) -> str:
    session_id = str(uuid.uuid4())
    payload = jwt.get_unverified_claims(access_token)
    user_id = payload.get("sub")  # str UUID

    r = get_redis()
    await r.setex(
        f"session:{session_id}",
        SESSION_TTL,
        json.dumps({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_id": user_id,
        })
    )
    await r.aclose()
    return session_id


async def get_session(session_id: str) -> dict | None:
    r = get_redis()
    data = await r.get(f"session:{session_id}")
    await r.aclose()
    if not data:
        return None
    return json.loads(data)


async def delete_session(session_id: str):
    r = get_redis()
    await r.delete(f"session:{session_id}")
    await r.aclose()