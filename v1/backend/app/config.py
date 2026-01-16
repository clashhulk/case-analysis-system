from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    app_name: str = "Case Analysis System"
    app_version: str = "0.1.0"
    debug: bool = True

    # Database
    database_url: str = "postgresql://postgres:postgres@postgres:5432/case_analysis"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Celery
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"

    # MinIO / S3
    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "case-documents"
    s3_use_ssl: bool = False

    # AI Services
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openai_enabled: bool = True  # Master switch for GPT-4 entity extraction
    ai_daily_budget_usd: float = 100.0
    ai_max_retries: int = 3

    # Vision AI (Claude Vision) - Fallback for poor quality documents
    vision_ai_enabled: bool = True
    vision_ai_quality_threshold: float = 0.5  # Use Vision AI if quality < 0.5
    vision_ai_max_pages: int = 10  # Limit pages to control cost

    # Text Extraction
    tesseract_path: str = "/usr/bin/tesseract"  # Path to tesseract executable for OCR
    max_text_length: int = 100000  # Maximum characters to extract from documents

    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS - Define allowed origins in .env file
    cors_origins: list[str] = []

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
