"""
Service layer
"""

from app.services.speech_recognition import get_speech_service, SpeechRecognitionService
from app.services.translation import get_translation_service, TranslationService
from app.services.animation import get_animation_service, AnimationService

__all__ = [
    "get_speech_service",
    "SpeechRecognitionService",
    "get_translation_service",
    "TranslationService",
    "get_animation_service",
    "AnimationService"
]
