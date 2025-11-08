"""
Speech to Sign Language - Main API Application
FastAPI-based backend supporting both on-device and cloud processing
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from typing import Optional, Dict, Any
import logging

from app.config import settings
from app.routes import speech, translation, animation, health, pose, avatar, validation
from app.database import engine, Base
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.auth import AuthMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Speech to Sign Language API",
    description="Backend API for converting speech to sign language with support for on-device and cloud processing",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(speech.router, prefix="/api/v1/speech", tags=["Speech Recognition"])
app.include_router(translation.router, prefix="/api/v1/translation", tags=["Translation"])
app.include_router(animation.router, prefix="/api/v1/animation", tags=["Animation"])
app.include_router(pose.router, tags=["Pose Extraction"])
app.include_router(avatar.router, tags=["Avatar Animation"])
app.include_router(validation.router, tags=["Sign Validation"])

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info(f"Starting Speech to Sign Language API in {settings.PROCESSING_MODE} mode")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Speech to Sign Language API")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Speech to Sign Language API",
        "version": "1.0.0",
        "mode": settings.PROCESSING_MODE,
        "docs": "/api/docs"
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level="info"
    )
