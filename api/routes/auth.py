import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_db
from db.models import User, RefreshToken, EmailVerificationToken
from services.auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_access_token,
    generate_totp_secret, generate_totp_qr, verify_totp,
    generate_verification_token, verification_token_expires, refresh_token_expires,
    send_verification_email
)

router = APIRouter()
bearer = HTTPBearer()


# ── Schemas ───────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TOTPVerifyRequest(BaseModel):
    temp_token: str
    code: str

class TOTPSetupVerifyRequest(BaseModel):
    code: str

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ── Dependencies ──────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db)
) -> User:
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


# ── Routes ────────────────────────────────────────────────

@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        is_verified=False,
        is_active=True,
        totp_enabled=False,
    )
    db.add(user)
    await db.flush()

    token_value = generate_verification_token()
    verification_token = EmailVerificationToken(
        user_id=user.id,
        token=token_value,
        expires_at=verification_token_expires(),
        used=False,
    )
    db.add(verification_token)
    await db.commit()

    send_verification_email(user.email, token_value)

    return {"message": "Account created. Please check your email to confirm your account."}


@router.get("/verify/{token}")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token == token,
            EmailVerificationToken.used == False
        )
    )
    vt = result.scalar_one_or_none()
    if not vt:
        raise HTTPException(status_code=400, detail="Invalid or already used token")
    if vt.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token expired")

    vt.used = True
    result = await db.execute(select(User).where(User.id == vt.user_id))
    user = result.scalar_one()
    user.is_verified = True
    await db.commit()

    return {"message": "Email confirmed. You can now log in."}


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email first")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    if user.totp_enabled:
        # Return a short-lived temp token to complete TOTP step
        temp_token = create_access_token(user.id)
        return {"requires_totp": True, "temp_token": temp_token}

    # No TOTP — issue tokens directly
    access_token = create_access_token(user.id)
    refresh_token_value = create_refresh_token()
    db.add(RefreshToken(
        user_id=user.id,
        token=refresh_token_value,
        expires_at=refresh_token_expires(),
    ))
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token_value)


@router.post("/totp/verify", response_model=TokenResponse)
async def totp_verify(body: TOTPVerifyRequest, db: AsyncSession = Depends(get_db)):
    user_id = decode_access_token(body.temp_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid temp token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.totp_secret:
        raise HTTPException(status_code=401, detail="Invalid request")

    if not verify_totp(user.totp_secret, body.code):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")

    access_token = create_access_token(user.id)
    refresh_token_value = create_refresh_token()
    db.add(RefreshToken(
        user_id=user.id,
        token=refresh_token_value,
        expires_at=refresh_token_expires(),
    ))
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token_value)


@router.post("/totp/setup")
async def totp_setup(current_user: User = Depends(get_current_user)):
    secret = generate_totp_secret()
    qr_base64 = generate_totp_qr(secret, current_user.email)
    # Secret returned but not saved yet — user must confirm with a valid code
    return {"secret": secret, "qr_code": qr_base64}


@router.post("/totp/enable")
async def totp_enable(
    body: TOTPSetupVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # The secret was passed back by the client after /totp/setup
    # In a real flow, store temp secret in Redis or signed JWT — simplified here
    raise HTTPException(status_code=501, detail="Pass secret in body — see TOTPEnableRequest")


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == body.refresh_token,
            RefreshToken.revoked == False
        )
    )
    rt = result.scalar_one_or_none()
    if not rt:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if rt.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    rt.revoked = True
    new_access = create_access_token(rt.user_id)
    new_refresh = create_refresh_token()
    db.add(RefreshToken(
        user_id=rt.user_id,
        token=new_refresh,
        expires_at=refresh_token_expires(),
    ))
    await db.commit()

    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


@router.post("/logout")
async def logout(
    body: RefreshRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == body.refresh_token,
            RefreshToken.user_id == current_user.id
        )
    )
    rt = result.scalar_one_or_none()
    if rt:
        rt.revoked = True
        await db.commit()
    return {"message": "Logged out"}


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "is_verified": current_user.is_verified,
        "totp_enabled": current_user.totp_enabled,
        "created_at": current_user.created_at,
    }