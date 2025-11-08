"""
Pydantic schemas for API request/response validation
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# Enums
class SignLanguage(str, Enum):
    ASL = "ASL"  # American Sign Language
    BSL = "BSL"  # British Sign Language
    ISL = "ISL"  # Irish Sign Language
    LSF = "LSF"  # French Sign Language (Langue des Signes Française)

class ProcessingMode(str, Enum):
    ON_DEVICE = "on-device"
    CLOUD = "cloud"
    HYBRID = "hybrid"

class SpeechProvider(str, Enum):
    WHISPER = "whisper"
    GOOGLE = "google"
    AZURE = "azure"
    AWS = "aws"

class AnimationFormat(str, Enum):
    MP4 = "mp4"
    WEBM = "webm"
    GIF = "gif"
    JSON = "json"  # Animation data

# Speech Recognition Schemas
class SpeechRecognitionRequest(BaseModel):
    audio_data: Optional[str] = Field(None, description="Base64 encoded audio data")
    audio_url: Optional[str] = Field(None, description="URL to audio file")
    language: str = Field("en-US", description="Source language code")
    provider: Optional[SpeechProvider] = Field(None, description="Override default provider")

    @validator('audio_data', 'audio_url')
    def check_audio_source(cls, v, values):
        if not values.get('audio_data') and not values.get('audio_url'):
            raise ValueError('Either audio_data or audio_url must be provided')
        return v

class SpeechRecognitionResponse(BaseModel):
    transcript: str
    confidence: float
    language: str
    processing_time_ms: int
    provider: str
    words: Optional[List[Dict[str, Any]]] = None  # Word-level timing info

# Translation Schemas
class TranslationRequest(BaseModel):
    text: str = Field(..., description="Text to translate to sign language")
    target_sign_language: SignLanguage = Field(SignLanguage.ASL, description="Target sign language")
    source_language: str = Field("en", description="Source language code")
    include_animation: bool = Field(True, description="Include animation data in response")
    use_cache: bool = Field(True, description="Use cached translations if available")

class SignUnit(BaseModel):
    """Individual sign in a sequence"""
    id: Optional[int] = None
    word: str
    gloss: str
    sign_language: str
    video_url: Optional[str] = None
    animation_data: Optional[Dict[str, Any]] = None
    timing: Optional[Dict[str, float]] = None  # start_time, end_time, duration

class TranslationResponse(BaseModel):
    original_text: str
    sign_language: str
    gloss_sequence: str  # Space-separated glosses
    sign_sequence: List[SignUnit]
    confidence_score: float
    processing_time_ms: int
    animation_url: Optional[str] = None
    cached: bool = False

# Animation Schemas
class AnimationRequest(BaseModel):
    sign_sequence: List[str] = Field(..., description="Array of sign glosses")
    sign_language: SignLanguage = Field(SignLanguage.ASL)
    output_format: AnimationFormat = Field(AnimationFormat.MP4)
    quality: str = Field("medium", description="Animation quality: low, medium, high")
    include_captions: bool = Field(True, description="Include captions in video")

class AnimationResponse(BaseModel):
    animation_url: str
    format: str
    duration_seconds: float
    file_size_bytes: int
    processing_time_ms: int
    thumbnail_url: Optional[str] = None

# Combined Pipeline Schemas
class SpeechToSignRequest(BaseModel):
    """Complete pipeline: Speech -> Text -> Sign"""
    audio_data: Optional[str] = Field(None, description="Base64 encoded audio data")
    audio_url: Optional[str] = Field(None, description="URL to audio file")
    target_sign_language: SignLanguage = Field(SignLanguage.ASL)
    output_format: AnimationFormat = Field(AnimationFormat.MP4)
    processing_mode: Optional[ProcessingMode] = None
    include_intermediate_results: bool = Field(False, description="Include transcript and gloss in response")

class SpeechToSignResponse(BaseModel):
    animation_url: str
    sign_language: str
    transcript: Optional[str] = None
    gloss_sequence: Optional[str] = None
    total_processing_time_ms: int
    processing_breakdown: Optional[Dict[str, int]] = None  # Time for each stage

# Dictionary Schemas
class SignEntryCreate(BaseModel):
    word: str
    sign_language: SignLanguage
    gloss: Optional[str] = None
    video_url: Optional[str] = None
    category: Optional[str] = None

class SignEntryResponse(BaseModel):
    id: int
    word: str
    sign_language: str
    gloss: Optional[str]
    video_url: Optional[str]
    animation_data: Optional[Dict[str, Any]]
    category: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# Health Check Schema
class HealthResponse(BaseModel):
    status: str
    version: str
    processing_mode: str
    services: Dict[str, str]
    timestamp: datetime

# Error Schema
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
