"""
Sign language animation API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.schemas import AnimationRequest, AnimationResponse, SpeechToSignRequest, SpeechToSignResponse
from app.services.animation import get_animation_service
from app.services.translation import get_translation_service
from app.services.speech_recognition import get_speech_service
from app.database import get_db
from app.config import settings

router = APIRouter()

@router.post("/generate", response_model=AnimationResponse)
async def generate_animation(request: AnimationRequest):
    """
    Generate sign language animation from sign sequence
    """
    animation_service = get_animation_service()

    try:
        # Convert sign sequence to sign data
        # In a real implementation, you'd look up each sign in the database
        sign_data_sequence = [
            {
                "gloss": gloss,
                "word": gloss.lower(),
                "sign_language": request.sign_language.value
            }
            for gloss in request.sign_sequence
        ]

        result = await animation_service.generate_animation(
            sign_data_sequence,
            request.sign_language.value,
            request.output_format.value,
            request.quality,
            request.include_captions,
            settings.ANIMATION_PROVIDER
        )

        return AnimationResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Animation generation failed: {str(e)}")

@router.post("/speech-to-sign", response_model=SpeechToSignResponse)
async def speech_to_sign(
    request: SpeechToSignRequest,
    db: Session = Depends(get_db)
):
    """
    Complete pipeline: Speech -> Text -> Sign Language -> Animation
    """
    import time
    total_start = time.time()
    processing_breakdown = {}

    try:
        # Step 1: Speech Recognition
        speech_service = get_speech_service()
        speech_start = time.time()

        if request.audio_data:
            speech_result = await speech_service.transcribe_from_base64(
                request.audio_data,
                "en-US"
            )
        elif request.audio_url:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(request.audio_url)
                audio_data = response.content

            speech_result = await speech_service.transcribe_audio(audio_data, "en-US")
        else:
            raise HTTPException(status_code=400, detail="Either audio_data or audio_url must be provided")

        processing_breakdown["speech_recognition"] = int((time.time() - speech_start) * 1000)
        transcript = speech_result["transcript"]

        if not transcript:
            raise HTTPException(status_code=400, detail="Could not transcribe audio")

        # Step 2: Translation
        translation_service = get_translation_service(db)
        translation_start = time.time()

        translation_result = await translation_service.translate_text(
            transcript,
            request.target_sign_language.value
        )

        processing_breakdown["translation"] = int((time.time() - translation_start) * 1000)

        # Step 3: Animation
        animation_service = get_animation_service()
        animation_start = time.time()

        animation_result = await animation_service.generate_animation(
            translation_result["sign_sequence"],
            request.target_sign_language.value,
            request.output_format.value,
            "medium",
            True,
            settings.ANIMATION_PROVIDER
        )

        processing_breakdown["animation"] = int((time.time() - animation_start) * 1000)

        # Build response
        total_time = int((time.time() - total_start) * 1000)

        response_data = {
            "animation_url": animation_result["animation_url"],
            "sign_language": request.target_sign_language.value,
            "total_processing_time_ms": total_time
        }

        if request.include_intermediate_results:
            response_data["transcript"] = transcript
            response_data["gloss_sequence"] = translation_result["gloss_sequence"]
            response_data["processing_breakdown"] = processing_breakdown

        return SpeechToSignResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech to sign pipeline failed: {str(e)}")
