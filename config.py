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

    # Digest schedule
    digest_hour: int = 7
    digest_minute: int = 0

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

