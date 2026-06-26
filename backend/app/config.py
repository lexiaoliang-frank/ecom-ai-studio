"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    # === App ===
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # === Database ===
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "ecom_ai_studio"
    postgres_user: str = "postgres"
    postgres_password: str = "change-me-in-production"

    # === Redis ===
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    # === MinIO / S3 ===
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "ecom-assets"
    minio_secure: bool = False

    # === LLM Aggregation ===
    llm_api_base: str = "https://api.tokenpony.cn/v1"
    llm_api_key: str = "your-llm-api-key-here"
    llm_model: str = "deepseek-v4-pro"
    llm_model_cheap: str = "gpt-4o-mini"

    # === Image Generation ===
    flux_api_key: str = ""
    flux_api_base: str = "https://api.replicate.com/v1"
    openai_api_key: str = ""
    tongyi_api_key: str = ""
    replicate_api_key: str = ""

    # === Video Generation ===
    runway_api_key: str = ""
    kling_api_key: str = ""
    kling_api_secret: str = ""
    luma_api_key: str = ""

    # === JWT ===
    jwt_secret_key: str = "change-me-to-a-random-string-at-least-32-chars"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # === Celery ===
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def minio_public_url(self) -> str:
        protocol = "https" if self.minio_secure else "http"
        return f"{protocol}://{self.minio_endpoint}/{self.minio_bucket}"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
