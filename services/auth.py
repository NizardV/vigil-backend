import uuid
import secrets
from datetime import datetime, timedelta, timezone

import pyotp
import qrcode
import io
import base64
from jose import jwt, JWTError
import resend
import bcrypt

from config import settings

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30
VERIFICATION_TOKEN_EXPIRE_HOURS = 24


# ── Password ─────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT ──────────────────────────────────────────────────

def create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def decode_access_token(token: str) -> uuid.UUID | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != "access":
            return None
        return uuid.UUID(payload["sub"])
    except JWTError:
        return None


# ── TOTP ─────────────────────────────────────────────────

def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name="Vigil"
    )


def generate_totp_qr(secret: str, email: str) -> str:
    uri = get_totp_uri(secret, email)
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def verify_totp(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


# ── Email verification token ──────────────────────────────

def generate_verification_token() -> str:
    return secrets.token_urlsafe(64)


def verification_token_expires() -> datetime:
    return datetime.utcnow() + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)


def refresh_token_expires() -> datetime:
    return datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)


# ── Email ─────────────────────────────────────────────────

def send_verification_email(email: str, token: str) -> None:
    resend.api_key = settings.resend_api_key
    verification_url = f"{settings.app_url}/email-confirmed?token={token}"
    resend.Emails.send({
        "from": f"Vigil <{settings.resend_from_email}>",
        "to": email,
        "subject": "Confirm your Vigil account",
        "html": f"""
        <h2>Welcome to Vigil</h2>
        <p>Click the link below to confirm your account:</p>
        <a href="{verification_url}">Confirm my account</a>
        <p>This link expires in 24 hours.</p>
        """
    })

# ── Email OTP ─────────────────────────────────────────────
def generate_otp_code() -> str:
    return str(secrets.randbelow(900000) + 100000)  # 6 chiffres

async def store_otp(redis_client, email: str, code: str) -> None:
    import json
    await redis_client.setex(f"otp:{email}", 300, code)  # 5 minutes TTL

async def verify_otp_code(redis_client, email: str, code: str) -> bool:
    stored = await redis_client.get(f"otp:{email}")
    if not stored:
        return False
    if stored == code:
        await redis_client.delete(f"otp:{email}")
        return True
    return False

def send_otp_email(email: str, code: str) -> None:
    resend.api_key = settings.resend_api_key
    resend.Emails.send({
        "from": f"Vigil <{settings.resend_from_email}>",
        "to": email,
        "subject": "Your Vigil login code",
        "html": f"""
        <h2>Your login code</h2>
        <p>Use this code to log in to Vigil:</p>
        <h1 style="font-size: 2rem; letter-spacing: 0.5rem;">{code}</h1>
        <p>This code expires in 5 minutes.</p>
        <p>If you didn't request this, ignore this email.</p>
        """
    })

