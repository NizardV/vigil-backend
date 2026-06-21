from fastapi import APIRouter, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
import os

router = APIRouter()

API_URL = os.getenv("API_URL", "http://localhost:8000/api")


@router.get("/login", response_class=HTMLResponse)
async def login_page(error: str = None):
    error_html = f'<p class="error">{error}</p>' if error else ""
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vigil - Login</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0e1117;
            color: #fafafa;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }}
        .container {{
            background: #1a1d27;
            padding: 2.5rem;
            border-radius: 12px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.4);
        }}
        h1 {{ font-size: 1.8rem; margin-bottom: 0.25rem; }}
        .subtitle {{ color: #888; font-size: 0.9rem; margin-bottom: 2rem; }}
        label {{ display: block; font-size: 0.85rem; color: #ccc; margin-bottom: 0.4rem; }}
        input {{
            width: 100%;
            padding: 0.65rem 0.9rem;
            background: #262730;
            border: 1px solid #333;
            border-radius: 8px;
            color: #fafafa;
            font-size: 0.95rem;
            margin-bottom: 1.2rem;
            outline: none;
            transition: border-color 0.2s;
        }}
        input:focus {{ border-color: #ff4b4b; }}
        button {{
            width: 100%;
            padding: 0.75rem;
            background: #ff4b4b;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            cursor: pointer;
            transition: background 0.2s;
        }}
        button:hover {{ background: #e03e3e; }}
        .error {{ color: #ff4b4b; font-size: 0.85rem; margin-bottom: 1rem; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Vigil</h1>
        <p class="subtitle">Automated tech watch system</p>
        {error_html}
        <form method="POST" action="/login">
            <label>Email</label>
            <input type="email" name="email" required autofocus>
            <label>Password</label>
            <input type="password" name="password" required>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>
""")


@router.post("/login")
async def login_submit(
    response: Response,
    email: str = Form(...),
    password: str = Form(...)
):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{API_URL}/auth/login", json={
                "email": email,
                "password": password
            })

        if resp.status_code == 200:
            data = resp.json()

            if data.get("requires_totp"):
                # TOTP à gérer plus tard
                return RedirectResponse(url="/login?error=TOTP+not+supported+via+this+flow", status_code=302)

            # Crée la session Redis
            async with httpx.AsyncClient() as client:
                session_resp = await client.post(f"{API_URL}/auth/session", json={
                    "access_token": data["access_token"],
                    "refresh_token": data["refresh_token"],
                    "token_type": "bearer"
                })

            if session_resp.status_code == 200:
                session_id = session_resp.json()["session_id"]
                redirect = RedirectResponse(url="/", status_code=302)
                redirect.set_cookie(
                    key="vigil_session_id",
                    value=session_id,
                    max_age=30 * 24 * 60 * 60,
                    httponly=True,
                    samesite="lax",
                    secure=True,
                    path="/",
                )
                return redirect

        elif resp.status_code == 403:
            detail = resp.json().get("detail", "")
            if "verify" in detail.lower():
                return RedirectResponse(url="/login?error=Please+verify+your+email+first", status_code=302)

        return RedirectResponse(url="/login?error=Invalid+email+or+password", status_code=302)

    except Exception as e:
        return RedirectResponse(url=f"/login?error=Connection+error", status_code=302)


@router.get("/logout")
async def logout(request: Request, response: Response):
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