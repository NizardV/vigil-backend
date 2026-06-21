from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
import os
from api.login_helpers import html_page

router = APIRouter()

API_URL = os.getenv("API_URL", "http://localhost:8000/api")


@router.get("/register", response_class=HTMLResponse)
async def register_page(error: str = None):
    error_html = f'<p class="error">{error}</p>' if error else ""
    body = f"""
        <p class="subtitle">Create your account</p>
        {error_html}
        <form method="POST" action="/register">
            <label>Email</label>
            <input type="email" name="email" required autofocus>
            <label>Password</label>
            <input type="password" name="password" required>
            <label>Confirm password</label>
            <input type="password" name="password2" required>
            <button type="submit">Create account</button>
        </form>
        <hr class="divider">
        <a href="/login">
            <button type="button" class="secondary">← Back to login</button>
        </a>
    """
    return HTMLResponse(content=html_page("Register", body))


@router.post("/register")
async def register_submit(
    email: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...)
):
    if password != password2:
        return RedirectResponse(url="/register?error=Passwords+do+not+match", status_code=302)

    if len(password) < 8:
        return RedirectResponse(url="/register?error=Password+must+be+at+least+8+characters", status_code=302)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{API_URL}/auth/register", json={
                "email": email,
                "password": password
            })

        if resp.status_code == 201:
            return RedirectResponse(url="/register/confirm", status_code=302)
        elif resp.status_code == 409:
            return RedirectResponse(url="/register?error=Email+already+registered", status_code=302)
        else:
            return RedirectResponse(url="/register?error=An+error+occurred", status_code=302)

    except Exception:
        return RedirectResponse(url="/register?error=Connection+error", status_code=302)


@router.get("/register/confirm", response_class=HTMLResponse)
async def register_confirm():
    body = """
        <p class="subtitle">Check your inbox</p>
        <p style="color: #ccc; margin-bottom: 2rem; line-height: 1.6;">
            We've sent a confirmation email to your address.
            Click the link in the email to activate your account.
        </p>
        <a href="/login">
            <button type="button">Go to login</button>
        </a>
    """
    return HTMLResponse(content=html_page("Confirm your email", body))


@router.get("/email-confirmed", response_class=HTMLResponse)
async def email_confirmed(token: str = None):
    if not token:
        return RedirectResponse(url="/login?error=Invalid+confirmation+link", status_code=302)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_URL}/auth/verify/{token}")

        if resp.status_code == 200:
            body = """
                <p class="subtitle">Email confirmed!</p>
                <p style="color: #ccc; margin-bottom: 2rem;">
                    Your account is now active. You can log in.
                </p>
                <a href="/login">
                    <button type="button">Login</button>
                </a>
            """
            return HTMLResponse(content=html_page("Email Confirmed", body))
        else:
            return RedirectResponse(url="/login?error=Invalid+or+expired+confirmation+link", status_code=302)

    except Exception:
        return RedirectResponse(url="/login?error=Connection+error", status_code=302)