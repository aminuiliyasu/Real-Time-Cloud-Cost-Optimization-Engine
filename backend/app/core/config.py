from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_env: str = "development"
    api_port: int = 8000
    api_key: str
    aws_region: str = "us-east-1"
    aws_profile: str = "default"
    aws_profiles: str = ""  # comma-separated profiles for multi-account ingestion
    gcp_projects: str = ""  # comma-separated project:zone entries
    gcp_default_zone: str = "us-central1-a"
    postgres_url: str
    redis_url: str

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()