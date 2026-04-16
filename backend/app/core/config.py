from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Market Influence Model API", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    cors_origins_raw: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")
    auth_db_path: str = Field(default="auth.sqlite3", alias="AUTH_DB_PATH")
    auth_token_ttl_days: int = Field(default=30, alias="AUTH_TOKEN_TTL_DAYS")
    daily_query_limit: int = Field(default=50, alias="DAILY_QUERY_LIMIT")
    owner_email: str | None = Field(default=None, alias="OWNER_EMAIL")
    owner_password: str | None = Field(default=None, alias="OWNER_PASSWORD")
    owner_full_name: str | None = Field(default=None, alias="OWNER_FULL_NAME")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5.4-mini", alias="OPENAI_MODEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
