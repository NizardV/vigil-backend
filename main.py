from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text
from config import settings
from db.session import engine, Base
from db import models  # noqa: F401
from api.routes import sources, themes, articles, feedback, digests, webhooks, discord, auth, login, login_otp, login_totp, register

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(
    title="Vigil API",
    description="Système de veille technologique automatisé avec scoring LLM",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(login.router, tags=["Login"])
app.include_router(login_otp.router, tags=["Login OTP"])
app.include_router(login_totp.router, tags=["Login TOTP"])
app.include_router(register.router, tags=["Register"])
app.include_router(themes.router,   prefix="/api/themes",   tags=["Themes"])
app.include_router(sources.router,  prefix="/api/sources",  tags=["Sources"])
app.include_router(articles.router, prefix="/api/articles", tags=["Articles"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])
app.include_router(digests.router,  prefix="/api/digests",  tags=["Digests"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])
app.include_router(discord.router,  prefix="/api/discord",  tags=["Discord"])
app.include_router(auth.router,     prefix="/api/auth",     tags=["Auth"])

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}