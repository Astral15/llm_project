from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "LLM Structured Output API"

    # --- Database ---
    # You can override this via env if you want, but this default works in docker
    SQLALCHEMY_DATABASE_URL: str = (
        "postgresql+psycopg2://appuser:apppassword@db:5432/llm_app_db"
    )

    # --- JWT / Auth ---
    JWT_SECRET_KEY: str = "super-secret-change-me"  # overridden by env in docker
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # --- MinIO / S3 storage ---
    # These MUST exist because images.py uses them
    MINIO_ENDPOINT: str = "http://minio:9000"
    MINIO_BUCKET: str = "llm-images"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin"

    # (optional) S3-style names if you want to use them elsewhere
    S3_ENDPOINT: str | None = None
    S3_BUCKET: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None

    # --- LLM ---
    OPENAI_API_KEY: str | None = None

    class Config:
        # used only for local dev; in docker, real env vars override these
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
