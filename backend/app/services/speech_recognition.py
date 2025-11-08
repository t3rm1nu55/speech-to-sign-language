"""
Speech Recognition Service
Supports multiple providers: Whisper (on-device), Google Cloud, Azure, AWS
"""

import base64
import io
import logging
import time
from typing import Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod

from app.config import settings

logger = logging.getLogger(__name__)

class SpeechRecognitionProvider(ABC):
    """Abstract base class for speech recognition providers"""

    @abstractmethod
    async def transcribe(self, audio_data: bytes, language: str = "en-US") -> Tuple[str, float]:
        """
        Transcribe audio to text
        Returns: (transcript, confidence)
        """
        pass

class WhisperProvider(SpeechRecognitionProvider):
    """OpenAI Whisper - On-device speech recognition"""

    def __init__(self):
        try:
            import whisper
            self.whisper = whisper
            self.model = None
            self.model_name = settings.WHISPER_MODEL
            logger.info(f"Whisper provider initialized with model: {self.model_name}")
        except ImportError:
            logger.error("Whisper not installed. Install with: pip install openai-whisper")
            raise

    def _load_model(self):
        """Lazy load model"""
        if self.model is None:
            logger.info(f"Loading Whisper model: {self.model_name}")
            self.model = self.whisper.load_model(self.model_name, device=settings.WHISPER_DEVICE)
        return self.model

    async def transcribe(self, audio_data: bytes, language: str = "en-US") -> Tuple[str, float]:
        """Transcribe using Whisper"""
        try:
            model = self._load_model()

            # Save audio to temporary file (Whisper requires file input)
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                temp_audio.write(audio_data)
                temp_audio_path = temp_audio.name

            # Transcribe
            language_code = language.split("-")[0]  # Convert en-US to en
            result = model.transcribe(
                temp_audio_path,
                language=language_code,
                fp16=(settings.WHISPER_DEVICE == "cuda")
            )

            # Cleanup
            import os
            os.unlink(temp_audio_path)

            transcript = result["text"].strip()
            # Whisper doesn't provide confidence, use a heuristic
            confidence = 0.9 if len(transcript) > 0 else 0.0

            logger.info(f"Whisper transcription: {transcript[:100]}...")
            return transcript, confidence

        except Exception as e:
            logger.error(f"Whisper transcription error: {str(e)}")
            raise

class GoogleCloudSpeechProvider(SpeechRecognitionProvider):
    """Google Cloud Speech-to-Text"""

    def __init__(self):
        try:
            from google.cloud import speech
            self.speech = speech
            self.client = speech.SpeechClient()
            logger.info("Google Cloud Speech provider initialized")
        except ImportError:
            logger.error("Google Cloud Speech not installed. Install with: pip install google-cloud-speech")
            raise

    async def transcribe(self, audio_data: bytes, language: str = "en-US") -> Tuple[str, float]:
        """Transcribe using Google Cloud Speech"""
        try:
            audio = self.speech.RecognitionAudio(content=audio_data)
            config = self.speech.RecognitionConfig(
                encoding=self.speech.RecognitionConfig.AudioEncoding.LINEAR16,
                language_code=language,
                enable_automatic_punctuation=True,
            )

            response = self.client.recognize(config=config, audio=audio)

            if not response.results:
                return "", 0.0

            result = response.results[0]
            transcript = result.alternatives[0].transcript
            confidence = result.alternatives[0].confidence

            logger.info(f"Google Cloud transcription: {transcript[:100]}...")
            return transcript, confidence

        except Exception as e:
            logger.error(f"Google Cloud transcription error: {str(e)}")
            raise

class AzureSpeechProvider(SpeechRecognitionProvider):
    """Azure Cognitive Services Speech"""

    def __init__(self):
        try:
            import azure.cognitiveservices.speech as speechsdk
            self.speechsdk = speechsdk
            speech_config = speechsdk.SpeechConfig(
                subscription=settings.AZURE_SPEECH_KEY,
                region=settings.AZURE_SPEECH_REGION
            )
            self.speech_config = speech_config
            logger.info("Azure Speech provider initialized")
        except ImportError:
            logger.error("Azure Speech not installed. Install with: pip install azure-cognitiveservices-speech")
            raise

    async def transcribe(self, audio_data: bytes, language: str = "en-US") -> Tuple[str, float]:
        """Transcribe using Azure Speech"""
        try:
            # Configure audio input
            audio_stream = self.speechsdk.audio.PushAudioInputStream()
            audio_config = self.speechsdk.audio.AudioConfig(stream=audio_stream)

            self.speech_config.speech_recognition_language = language

            # Create recognizer
            speech_recognizer = self.speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )

            # Write audio data
            audio_stream.write(audio_data)
            audio_stream.close()

            # Recognize
            result = speech_recognizer.recognize_once()

            if result.reason == self.speechsdk.ResultReason.RecognizedSpeech:
                # Azure doesn't provide confidence directly, use a heuristic
                confidence = 0.9
                logger.info(f"Azure transcription: {result.text[:100]}...")
                return result.text, confidence
            else:
                logger.warning(f"Azure recognition failed: {result.reason}")
                return "", 0.0

        except Exception as e:
            logger.error(f"Azure transcription error: {str(e)}")
            raise

class SpeechRecognitionService:
    """Main speech recognition service with provider selection"""

    def __init__(self):
        self.providers: Dict[str, SpeechRecognitionProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize available providers based on configuration"""
        # Always try to initialize Whisper for on-device processing
        try:
            self.providers["whisper"] = WhisperProvider()
        except Exception as e:
            logger.warning(f"Could not initialize Whisper: {str(e)}")

        # Initialize cloud providers if credentials are available
        if settings.GOOGLE_CLOUD_PROJECT and settings.GOOGLE_APPLICATION_CREDENTIALS:
            try:
                self.providers["google"] = GoogleCloudSpeechProvider()
            except Exception as e:
                logger.warning(f"Could not initialize Google Cloud Speech: {str(e)}")

        if settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION:
            try:
                self.providers["azure"] = AzureSpeechProvider()
            except Exception as e:
                logger.warning(f"Could not initialize Azure Speech: {str(e)}")

        logger.info(f"Initialized speech providers: {list(self.providers.keys())}")

    async def transcribe_audio(
        self,
        audio_data: bytes,
        language: str = "en-US",
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text
        Args:
            audio_data: Raw audio bytes
            language: Language code (e.g., "en-US")
            provider: Override provider (None uses default from settings)
        Returns:
            Dict with transcript, confidence, provider, and processing time
        """
        start_time = time.time()

        # Select provider
        provider_name = provider or settings.SPEECH_PROVIDER
        if provider_name not in self.providers:
            # Fallback to first available provider
            if not self.providers:
                raise ValueError("No speech recognition providers available")
            provider_name = list(self.providers.keys())[0]
            logger.warning(f"Requested provider not available, using: {provider_name}")

        provider_instance = self.providers[provider_name]

        # Transcribe
        transcript, confidence = await provider_instance.transcribe(audio_data, language)

        processing_time = int((time.time() - start_time) * 1000)

        return {
            "transcript": transcript,
            "confidence": confidence,
            "language": language,
            "provider": provider_name,
            "processing_time_ms": processing_time
        }

    async def transcribe_from_base64(
        self,
        audio_base64: str,
        language: str = "en-US",
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transcribe from base64 encoded audio"""
        audio_data = base64.b64decode(audio_base64)
        return await self.transcribe_audio(audio_data, language, provider)

    def get_available_providers(self) -> list:
        """Get list of available providers"""
        return list(self.providers.keys())

# Global service instance
_speech_service: Optional[SpeechRecognitionService] = None

def get_speech_service() -> SpeechRecognitionService:
    """Get or create speech recognition service instance"""
    global _speech_service
    if _speech_service is None:
        _speech_service = SpeechRecognitionService()
    return _speech_service
