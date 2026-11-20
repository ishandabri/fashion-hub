from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./data/store.db"
    bootstrap_username: str = "owner"
    bootstrap_password: str = "change-this-password"
    frontend_origin: str = "http://localhost:4173"
    app_version: str = "0.1.0"
    app_revision: str = "dev"
    app_built_at: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

