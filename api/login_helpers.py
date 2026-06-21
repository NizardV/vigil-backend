from fastapi.responses import RedirectResponse
from services.session import create_session

BASE_CSS = """
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: #0e1117;
        color: #fafafa;
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
    }
    .container {
        background: #1a1d27;
        padding: 2.5rem;
        border-radius: 12px;
        width: 100%;
        max-width: 400px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    }
    h1 { font-size: 1.8rem; margin-bottom: 0.25rem; }
    .subtitle { color: #888; font-size: 0.9rem; margin-bottom: 2rem; }
    .hint { color: #888; font-size: 0.85rem; margin-bottom: 0.5rem; }
    .highlight { color: #ff4b4b; font-size: 0.9rem; margin-bottom: 2rem; }
    label { display: block; font-size: 0.85rem; color: #ccc; margin-bottom: 0.4rem; }
    input {
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
    }
    input:focus { border-color: #ff4b4b; }
    input.code {
        font-size: 1.5rem;
        letter-spacing: 0.5rem;
        text-align: center;
    }
    button {
        width: 100%;
        padding: 0.75rem;
        background: #ff4b4b;
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 1rem;
        cursor: pointer;
        transition: background 0.2s;
        margin-bottom: 0.75rem;
    }
    button:hover { background: #e03e3e; }
    button.secondary {
        background: transparent;
        border: 1px solid #444;
        color: #aaa;
    }
    button.secondary:hover { background: #262730; border-color: #666; color: #fff; }
    .error { color: #ff4b4b; font-size: 0.85rem; margin-bottom: 1rem; }
    .divider { border: none; border-top: 1px solid #333; margin: 1.5rem 0; }
"""


def html_page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vigil - {title}</title>
    <style>{BASE_CSS}</style>
</head>
<body>
    <div class="container">
        <h1>🔍 Vigil</h1>
        {body}
    </div>
</body>
</html>"""


async def create_session_redirect(access_token: str, refresh_token: str, redirect_url: str = "/") -> RedirectResponse:
    session_id = await create_session(access_token, refresh_token)
    redirect = RedirectResponse(url=redirect_url, status_code=302)
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