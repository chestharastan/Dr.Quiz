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
    question_images_dir: str = "/home/thareah/Extract/output_images/images"
    qa_images_dir: str = "/home/thareah/Quiz_Dr/output_qa"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
