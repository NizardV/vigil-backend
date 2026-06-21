from fastapi import APIRouter, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
import os
from api.login_helpers import html_page, create_session_redirect

router = APIRouter()

API_URL = os.getenv("API_URL", "http://localhost:8000/api")


@router.get("/login", response_class=HTMLResponse)
async def login_page(error: str = None):
    error_html = f'<p class="error">{error}</p>' if error else ""
    body = f"""
        <p class="subtitle">Automated tech watch system</p>
        {error_html}
        <form method="POST" action="/login">
            <label>Email</label>
            <input type="email" name="email" required autofocus>
            <label>Password</label>
            <input type="password" name="password" required>
            <button type="submit">Login</button>
        </form>
        <hr class="divider">
        <a href="/login/otp">
            <button type="button" class="secondary">Login with email code</button>
        </a>
        <a href="/register">
            <button type="button" class="secondary">Create account</button>
        </a>
    """
    return HTMLResponse(content=html_page("Login", body))


@router.post("/login")
async def login_submit(response: Response, email: str = Form(...), password: str = Form(...)):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{API_URL}/auth/login", json={
                "email": email,
                "password": password
            })

        if resp.status_code == 200:
            data = resp.json()

            if data.get("requires_totp"):
                return RedirectResponse(
                    url=f"/login/totp?temp_token={data['temp_token']}",
                    status_code=302
                )

            async with httpx.AsyncClient() as client:
                session_resp = await client.post(f"{API_URL}/auth/session", json={
                    "access_token": data["access_token"],
                    "refresh_token": data["refresh_token"],
                    "token_type": "bearer"
                })

            if session_resp.status_code == 200:
                return await create_session_redirect(
                    data["access_token"],
                    data["refresh_token"]
                )

        elif resp.status_code == 403:
            detail = resp.json().get("detail", "")
            if "verify" in detail.lower():
                return RedirectResponse(url="/login?error=Please+verify+your+email+first", status_code=302)

        return RedirectResponse(url="/login?error=Invalid+email+or+password", status_code=302)

    except Exception:
        return RedirectResponse(url="/login?error=Connection+error", status_code=302)


@router.get("/logout")
async def logout(request: Request):
    session_id = request.cookies.get("vigil_session_id")
    if session_id:
        try:
            async with httpx.AsyncClient() as client:
                await client.delete(f"{API_URL}/auth/session/me", cookies={"vigil_session_id": session_id})
        except Exception:
            pass

    redirect = RedirectResponse(url="/login", status_code=302)
    redirect.delete_cookie(key="vigil_session_id", path="/")
    return redirect