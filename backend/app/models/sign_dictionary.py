"""
Database models for sign language dictionary
"""

from sqlalchemy import Column, Integer, String, JSON, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.database import Base

class SignEntry(Base):
    """Sign language dictionary entry"""
    __tablename__ = "sign_entries"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(255), nullable=False, index=True)
    sign_language = Column(String(10), nullable=False, index=True)  # ASL, BSL, etc.

    # Sign representation
    gloss = Column(String(255))  # Standard gloss notation
    hamnosys = Column(Text)  # HamNoSys notation for sign
    sigml = Column(Text)  # SiGML representation

    # Media references
    video_url = Column(String(500))
    animation_data = Column(JSON)  # 3D animation keyframes
    thumbnail_url = Column(String(500))

    # Metadata
    category = Column(String(100))  # noun, verb, adjective, etc.
    difficulty = Column(Integer, default=1)  # 1-5 scale
    frequency = Column(Integer, default=0)  # Usage frequency

    # Linguistic data
    handshape = Column(String(100))
    location = Column(String(100))
    movement = Column(String(100))
    palm_orientation = Column(String(100))
    non_manual_markers = Column(JSON)

    # Variations
    regional_variations = Column(JSON)
    alternative_signs = Column(JSON)

    # Status
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SignPhrase(Base):
    """Common phrases in sign language"""
    __tablename__ = "sign_phrases"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    sign_language = Column(String(10), nullable=False, index=True)

    # Sign sequence
    sign_sequence = Column(JSON)  # Array of sign IDs or glosses
    gloss_sequence = Column(Text)  # Space-separated glosses

    # Media
    video_url = Column(String(500))
    animation_data = Column(JSON)

    # Metadata
    category = Column(String(100))
    usage_count = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class TranslationCache(Base):
    """Cache for text to sign translations"""
    __tablename__ = "translation_cache"

    id = Column(Integer, primary_key=True, index=True)
    source_text = Column(Text, nullable=False, index=True)
    source_language = Column(String(10), default="en")
    sign_language = Column(String(10), nullable=False)

    # Translation result
    gloss_output = Column(Text)
    sign_sequence = Column(JSON)
    animation_sequence = Column(JSON)

    # Metadata
    translation_method = Column(String(50))  # rule-based, ml-based
    confidence_score = Column(Integer)
    processing_time_ms = Column(Integer)

    # Usage tracking
    usage_count = Column(Integer, default=1)
    last_used = Column(DateTime(timezone=True), server_default=func.now())

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserSession(Base):
    """User session tracking"""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)

    # User preferences
    preferred_sign_language = Column(String(10), default="ASL")
    processing_mode = Column(String(20))  # on-device, cloud, hybrid

    # Session metadata
    device_type = Column(String(50))  # web, ios, android
    user_agent = Column(String(500))

    # Statistics
    total_translations = Column(Integer, default=0)
    total_speech_duration_seconds = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
