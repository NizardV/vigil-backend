from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from config import settings
from db.session import engine, Base
from db import models, models_projects  # noqa: F401
from api.routes import sources, themes, articles, feedback, digests, webhooks, discord, auth, login, login_otp, login_totp, register, projects, github_webhooks

@asynccontextmanager
async def lifespan(app: FastAPI):
    # DDL "IF NOT EXISTS" en AUTOCOMMIT : avec --workers 2, les deux process
    # peuvent tenter la creation en meme temps au premier boot. IF NOT EXISTS
    # ne protege pas contre cette race (check-then-create non atomique cote
    # Postgres), donc on catch l'erreur du perdant plutot que de laisser
    # le worker crasher.
    async with engine.connect() as conn:
        autocommit_conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
        for stmt in (
            "CREATE EXTENSION IF NOT EXISTS vector",
            "CREATE SCHEMA IF NOT EXISTS projects",
        ):
            try:
                await autocommit_conn.execute(text(stmt))
            except IntegrityError:
                pass  # deja cree par l'autre worker, rien a faire

    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
        except IntegrityError:
            pass  # meme race que ci-dessus, sur une table cette fois
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
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(github_webhooks.router, prefix="/api/github-webhooks", tags=["GitHub Webhooks"])

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}