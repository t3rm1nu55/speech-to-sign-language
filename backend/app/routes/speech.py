"""
Speech recognition API endpoints
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
import base64

from app.schemas import SpeechRecognitionRequest, SpeechRecognitionResponse
from app.services.speech_recognition import get_speech_service

router = APIRouter()

@router.post("/recognize", response_model=SpeechRecognitionResponse)
async def recognize_speech(request: SpeechRecognitionRequest):
    """
    Recognize speech from audio data
    Accepts base64 encoded audio or audio URL
    """
    speech_service = get_speech_service()

    try:
        if request.audio_data:
            # Decode base64 audio
            result = await speech_service.transcribe_from_base64(
                request.audio_data,
                request.language,
                request.provider
            )
        elif request.audio_url:
            # Fetch audio from URL
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(request.audio_url)
                audio_data = response.content

            result = await speech_service.transcribe_audio(
                audio_data,
                request.language,
                request.provider
            )
        else:
            raise HTTPException(status_code=400, detail="Either audio_data or audio_url must be provided")

        return SpeechRecognitionResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech recognition failed: {str(e)}")

@router.post("/recognize/upload", response_model=SpeechRecognitionResponse)
async def recognize_speech_upload(
    audio_file: UploadFile = File(...),
    language: str = Form("en-US"),
    provider: Optional[str] = Form(None)
):
    """
    Recognize speech from uploaded audio file
    """
    speech_service = get_speech_service()

    try:
        # Read audio file
        audio_data = await audio_file.read()

        # Transcribe
        result = await speech_service.transcribe_audio(
            audio_data,
            language,
            provider
        )

        return SpeechRecognitionResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech recognition failed: {str(e)}")

@router.get("/providers")
async def list_providers():
    """List available speech recognition providers"""
    speech_service = get_speech_service()
    providers = speech_service.get_available_providers()

    return {
        "providers": providers,
        "default": speech_service.providers.get(speech_service.providers, "whisper")
    }
