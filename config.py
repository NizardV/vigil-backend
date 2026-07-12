from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL
    database_url: str

    # Redis / Celery
    redis_url: str
    celery_broker_url: str
    celery_result_backend: str

    # LLM
    gemini_api_key: str
    gemini_model: str = "gemini-1.5-flash"

    # FastAPI
    secret_key: str
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # Discord
    discord_webhook_url: str = ""
    discord_public_key: str = ""
    discord_bot_token: str = ""

    # Projects module - GitHub
    github_token: str = ""
    github_webhook_secret: str = ""

    # Projects module - Notion
    notion_api_key: str = ""
    notion_projects_db_id: str = ""

    # Projects module - Discord (digest event-driven dedie)
    discord_projects_webhook_url: str = ""

    # Digest schedule
    digest_hour: int = 7
    digest_minute: int = 0

    # Resend
    resend_api_key: str = ""
    resend_from_email: str = "noreply@projet-cyna.fr"

    # App
    app_url: str = "https://vigil.projet-cyna.fr"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

