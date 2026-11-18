from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    secret_key: str = "change-me"
    database_url: str = "sqlite:///./data/store.db"
    bootstrap_username: str = "owner"
    bootstrap_password: str = "change-this-password"
    frontend_origin: str = "http://localhost:4173"
    business_timezone: str = "Asia/Kolkata"
    backup_dir: str = "./backups"
    public_hostname: str = "localhost"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

