"""
Centralized app configuration. Everything secret or environment-specific is
read from env vars (see .env.example) — never hardcoded, never sent to the
frontend.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    database_url: str = "sqlite+aiosqlite:///./relay.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # AI
    anthropic_api_key: str = ""
    ai_model: str = "claude-sonnet-4-6"
    ai_max_concurrency: int = 10
    ai_max_retries: int = 3

    # Email OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    ms_client_id: str = ""
    ms_client_secret: str = ""
    ms_redirect_uri: str = "http://localhost:8000/auth/microsoft/callback"

    # Token encryption (Fernet key — see .env.example for how to generate one)
    token_encryption_key: str = ""

    # Where the frontend lives, for post-OAuth redirects
    frontend_url: str = "http://localhost:5173"

    # CORS
    allowed_origins: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
