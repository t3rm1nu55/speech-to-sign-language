"""
Text to Sign Language translation API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.schemas import TranslationRequest, TranslationResponse
from app.services.translation import get_translation_service
from app.database import get_db

router = APIRouter()

@router.post("/translate", response_model=TranslationResponse)
async def translate_text(
    request: TranslationRequest,
    db: Session = Depends(get_db)
):
    """
    Translate text to sign language
    Returns gloss sequence and sign data
    """
    translation_service = get_translation_service(db)

    try:
        result = await translation_service.translate_text(
            request.text,
            request.target_sign_language.value,
            request.use_cache
        )

        # Format response
        from app.schemas import SignUnit
        sign_units = [SignUnit(**sign) for sign in result["sign_sequence"]]

        return TranslationResponse(
            original_text=result["original_text"],
            sign_language=result["sign_language"],
            gloss_sequence=result["gloss_sequence"],
            sign_sequence=sign_units,
            confidence_score=result["confidence_score"],
            processing_time_ms=result["processing_time_ms"],
            animation_url=result.get("animation_url"),
            cached=result.get("cached", False)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

@router.post("/batch-translate")
async def batch_translate(
    texts: list[str],
    target_sign_language: str = "ASL",
    db: Session = Depends(get_db)
):
    """
    Translate multiple texts to sign language
    """
    translation_service = get_translation_service(db)

    try:
        results = await translation_service.batch_translate(texts, target_sign_language)
        return {"translations": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch translation failed: {str(e)}")
