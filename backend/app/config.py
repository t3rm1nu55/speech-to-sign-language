"""
Configuration settings for the Speech to Sign Language application
Supports both on-device and cloud processing modes
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache
import os

class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "Speech to Sign Language API"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Processing Mode: "on-device", "cloud", "hybrid"
    PROCESSING_MODE: str = os.getenv("PROCESSING_MODE", "hybrid")

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
    ]

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/sign_language_db"
    )

    # Redis Cache
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour

    # Speech Recognition Settings
    SPEECH_PROVIDER: str = os.getenv("SPEECH_PROVIDER", "whisper")  # whisper, google, azure, aws
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")  # cpu, cuda

    # Google Cloud Speech
    GOOGLE_CLOUD_PROJECT: Optional[str] = os.getenv("GOOGLE_CLOUD_PROJECT")
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    # Azure Speech
    AZURE_SPEECH_KEY: Optional[str] = os.getenv("AZURE_SPEECH_KEY")
    AZURE_SPEECH_REGION: Optional[str] = os.getenv("AZURE_SPEECH_REGION")

    # AWS Transcribe
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION: Optional[str] = os.getenv("AWS_REGION", "us-east-1")

    # Sign Language Settings
    DEFAULT_SIGN_LANGUAGE: str = os.getenv("DEFAULT_SIGN_LANGUAGE", "ASL")  # ASL, BSL, etc.
    SUPPORTED_SIGN_LANGUAGES: List[str] = ["ASL", "BSL", "ISL", "LSF"]

    # Translation Settings
    USE_NLP_TRANSLATION: bool = os.getenv("USE_NLP_TRANSLATION", "true").lower() == "true"
    TRANSLATION_MODEL: str = os.getenv("TRANSLATION_MODEL", "rule-based")  # rule-based, ml-based

    # Animation Settings
    ANIMATION_PROVIDER: str = os.getenv("ANIMATION_PROVIDER", "avatar")  # avatar, video, hybrid
    AVATAR_QUALITY: str = os.getenv("AVATAR_QUALITY", "medium")  # low, medium, high
    VIDEO_LIBRARY_PATH: str = os.getenv("VIDEO_LIBRARY_PATH", "./data/sign_videos")
    ANIMATION_OUTPUT_FORMAT: str = os.getenv("ANIMATION_OUTPUT_FORMAT", "mp4")  # mp4, webm, gif

    # Storage
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "./outputs")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB

    # Security
    API_KEY_ENABLED: bool = os.getenv("API_KEY_ENABLED", "false").lower() == "true"
    API_KEY_HEADER: str = "X-API-Key"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # Performance
    ENABLE_ASYNC_PROCESSING: bool = os.getenv("ENABLE_ASYNC_PROCESSING", "true").lower() == "true"
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "4"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE", "./logs/app.log")

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

settings = get_settings()
