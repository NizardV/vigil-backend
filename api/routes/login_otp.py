from fastapi import APIRouter, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from api.login_helpers import html_page, create_session_redirect

router = APIRouter()


@router.get("/login/otp", response_class=HTMLResponse)
async def otp_request_page(error: str = None):
    error_html = f'<p class="error">{error}</p>' if error else ""
    body = f"""
        <p class="subtitle">Login with email code</p>
        {error_html}
        <form method="POST" action="/login/otp">
            <label>Email</label>
            <input type="email" name="email" required autofocus>
            <button type="submit">Send code</button>
        </form>
        <hr class="divider">
        <a href="/login">
            <button type="button" class="secondary">← Back to login</button>
        </a>
    """
    return HTMLResponse(content=html_page("Login with OTP", body))


@router.post("/login/otp")
async def otp_request_submit(email: str = Form(...)):
    from services.session import get_redis
    from services.auth import generate_otp_code, store_otp, send_otp_email
    from db.session import AsyncSessionLocal
    from db.models import User
    from sqlalchemy import select

    r = get_redis()
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(
                    User.email == email,
                    User.is_active == True,
                    User.is_verified == True
                )
            )
            user = result.scalar_one_or_none()

        if user:
            code = generate_otp_code()
            await store_otp(r, email, code)
            send_otp_email(email, code)
    except Exception:
        pass
    finally:
        await r.aclose()

    return RedirectResponse(url=f"/login/otp/verify?email={email}", status_code=302)


@router.get("/login/otp/verify", response_class=HTMLResponse)
async def otp_verify_page(email: str, error: str = None):
    error_html = f'<p class="error">{error}</p>' if error else ""
    body = f"""
        <p class="subtitle">Enter the code sent to</p>
        <p class="highlight">{email}</p>
        {error_html}
        <form method="POST" action="/login/otp/verify">
            <input type="hidden" name="email" value="{email}">
            <label>6-digit code</label>
            <input type="text" class="code" name="code" maxlength="6" required autofocus placeholder="000000">
            <button type="submit">Verify</button>
        </form>
        <hr class="divider">
        <a href="/login/otp">
            <button type="button" class="secondary">← Resend code</button>
        </a>
    """
    return HTMLResponse(content=html_page("Enter Code", body))


@router.post("/login/otp/verify")
async def otp_verify_submit(response: Response, email: str = Form(...), code: str = Form(...)):
    from services.session import get_redis, create_session
    from services.auth import verify_otp_code, create_access_token, create_refresh_token, refresh_token_expires
    from db.session import AsyncSessionLocal
    from db.models import User, RefreshToken
    from sqlalchemy import select

    r = get_redis()
    try:
        valid = await verify_otp_code(r, email, code)
        if not valid:
            return RedirectResponse(
                url=f"/login/otp/verify?email={email}&error=Invalid+or+expired+code",
                status_code=302
            )

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(User.email == email, User.is_active == True)
            )
            user = result.scalar_one_or_none()

        if not user:
            return RedirectResponse(url="/login/otp?error=User+not+found", status_code=302)

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

    finally:
        await r.aclose()