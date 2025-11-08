"""
Health check and system status endpoints
"""

from fastapi import APIRouter, Depends
from datetime import datetime
from app.config import settings
from app.schemas import HealthResponse
from app.services.speech_recognition import get_speech_service

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    speech_service = get_speech_service()
    available_providers = speech_service.get_available_providers()

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        processing_mode=settings.PROCESSING_MODE,
        services={
            "speech_recognition": "available" if available_providers else "unavailable",
            "translation": "available",
            "animation": "available",
            "database": "available",
            "cache": "available" if settings.CACHE_ENABLED else "disabled"
        },
        timestamp=datetime.now()
    )

@router.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    return {"status": "ready"}

@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive"}
