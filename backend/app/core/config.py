import os
from functools import lru_cache

def _env(k: str, default: str | None = None) -> str:
    v = os.getenv(k, default)
    if v is None:
        raise RuntimeError(f"Missing env: {k}")
    return v

class Settings:
    # project
    PROJECT_NAME = "LLM Structured Output API"

    # db
    SQLALCHEMY_DATABASE_URL = _env(
        "SQLALCHEMY_DATABASE_URL",
        "postgresql+psycopg2://appuser:apppassword@db:5432/llm_app_db",
    )

    # jwt
    JWT_SECRET_KEY = _env("JWT_SECRET_KEY", "change-me-in-prod")
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    # storage (MinIO / S3-compatible)
    MINIO_ENDPOINT = _env("MINIO_ENDPOINT", "http://minio:9000")
    MINIO_BUCKET = _env("MINIO_BUCKET", "llm-images")
    MINIO_ROOT_USER = _env("MINIO_ROOT_USER", "minioadmin")
    MINIO_ROOT_PASSWORD = _env("MINIO_ROOT_PASSWORD", "minioadmin")

    # optional S3-style names
    S3_ENDPOINT = os.getenv("S3_ENDPOINT") or MINIO_ENDPOINT
    S3_BUCKET = os.getenv("S3_BUCKET") or MINIO_BUCKET
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY") or MINIO_ROOT_USER
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY") or MINIO_ROOT_PASSWORD

    # LLM
    GEMINI_API_KEY = _env("GEMINI_API_KEY", "")
    GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")

@lru_cache
def get_settings() -> Settings:
    return Settings()
