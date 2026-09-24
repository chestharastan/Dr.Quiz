from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    cors_origins: str = "http://localhost:3000"
    secret_key: str
    access_token_expire_minutes: int = 60 * 24 * 7
    cookie_secure: bool = False
    initial_admin_username: str = "admin"
    initial_admin_password: str | None = None

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, url: str) -> str:
        # Supabase and Render hand out postgres:// or postgresql:// URLs; SQLAlchemy would then look for psycopg2.
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix) :]
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
