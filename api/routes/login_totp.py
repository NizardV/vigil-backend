from fastapi import APIRouter, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from api.login_helpers import html_page, create_session_redirect

router = APIRouter()


@router.get("/login/totp", response_class=HTMLResponse)
async def totp_verify_page(temp_token: str, error: str = None):
    error_html = f'<p class="error">{error}</p>' if error else ""
    body = f"""
        <p class="subtitle">Two-Factor Authentication</p>
        <p class="hint">Enter the code from your authenticator app</p>
        {error_html}
        <form method="POST" action="/login/totp">
            <input type="hidden" name="temp_token" value="{temp_token}">
            <label>6-digit code</label>
            <input type="text" class="code" name="code" maxlength="6" required autofocus placeholder="000000">
            <button type="submit">Verify</button>
        </form>
        <hr class="divider">
        <a href="/login">
            <button type="button" class="secondary">← Back to login</button>
        </a>
    """
    return HTMLResponse(content=html_page("Two-Factor Authentication", body))


@router.post("/login/totp")
async def totp_verify_submit(response: Response, temp_token: str = Form(...), code: str = Form(...)):
    from services.auth import (
        decode_pending_2fa_token, verify_totp,
        create_access_token, create_refresh_token, refresh_token_expires
    )
    from db.session import AsyncSessionLocal
    from db.models import User, RefreshToken
    from sqlalchemy import select

    user_id = decode_pending_2fa_token(temp_token)
    if not user_id:
        return RedirectResponse(url="/login?error=Invalid+or+expired+session", status_code=302)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

    if not user or not user.totp_secret:
        return RedirectResponse(url="/login?error=Invalid+request", status_code=302)

    if not verify_totp(user.totp_secret, code):
        return RedirectResponse(
            url=f"/login/totp?temp_token={temp_token}&error=Invalid+code",
            status_code=302
        )

    access_token = create_access_token(user.id)
    refresh_token_value = create_refresh_token()

    async with AsyncSessionLocal() as db:
        db.add(RefreshToken(
            user_id=user.id,
            token=refresh_token_value,
            expires_at=refresh_token_expires(),
        ))
        await db.commit()

    return await create_session_redirect(access_token, refresh_token_value)