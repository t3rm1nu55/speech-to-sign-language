"""
Validation API Endpoints
Provides access to sign validation and analysis
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from app.services.sign_validation import SignValidationService
from app.models.sign_description import (
    SignDescription, SignValidationResult,
    Handshape, Location, Movement, PalmOrientation, HandConfiguration
)

router = APIRouter(prefix="/api/validation")

# Initialize service
validation_service = SignValidationService()


class ValidateSignRequest(BaseModel):
    """Request to validate a sign interpretation"""
    video_url: str
    expected_description: SignDescription
    max_frames: int = 30


class ValidateSignResponse(BaseModel):
    """Response with validation results"""
    result: SignValidationResult


class AnalyzeVideoRequest(BaseModel):
    """Request to analyze video and extract features"""
    video_url: str
    max_frames: int = 30


class AnalyzeVideoResponse(BaseModel):
    """Response with extracted features"""
    success: bool
    video_url: str
    frames_analyzed: int
    video_quality_score: float
    pose_detection_rate: float
    extracted_features: Dict
    diagnostics: Dict[str, str]


class CompareSignsRequest(BaseModel):
    """Request to compare multiple interpretations of same sign"""
    gloss: str
    video_urls: List[str]
    expected_description: Optional[SignDescription] = None
    max_frames: int = 30


class CompareSignsResponse(BaseModel):
    """Response comparing multiple videos"""
    gloss: str
    total_videos: int
    comparison_results: List[Dict]
    best_video: Optional[str] = None
    worst_video: Optional[str] = None
    average_quality: float


@router.post("/validate-sign", response_model=ValidateSignResponse)
async def validate_sign(request: ValidateSignRequest):
    """
    Validate a sign interpretation against expected linguistic description.

    Performs comprehensive validation:
    - Extracts pose from video
    - Compares handshape, location, movement, palm orientation
    - Generates diagnostic report
    - Provides improvement suggestions
    """
    try:
        result = validation_service.validate_sign(
            video_url=request.video_url,
            expected_description=request.expected_description,
            max_frames=request.max_frames
        )

        return ValidateSignResponse(result=result)

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Validation failed: {str(e)}"
        )


@router.post("/analyze-video", response_model=AnalyzeVideoResponse)
async def analyze_video(request: AnalyzeVideoRequest):
    """
    Analyze a sign video and extract features without comparison.

    Useful for:
    - Exploring unknown signs
    - Quality assessment
    - Feature extraction for research
    """
    try:
        # Extract pose data
        pose_data = validation_service.pose_service.extract_pose_from_video(
            request.video_url,
            max_frames=request.max_frames
        )

        if not pose_data.get('success', False):
            return AnalyzeVideoResponse(
                success=False,
                video_url=request.video_url,
                frames_analyzed=0,
                video_quality_score=0.0,
                pose_detection_rate=0.0,
                extracted_features={},
                diagnostics={'error': 'Failed to extract pose from video'}
            )

        frames = pose_data.get('frames', [])

        # Assess quality
        quality_score = validation_service._assess_video_quality(frames)

        # Calculate detection rate
        frames_with_pose = sum(
            1 for f in frames
            if f.get('pose') and len(f['pose']) >= 33
        )
        detection_rate = frames_with_pose / len(frames) if frames else 0.0

        # Extract features
        features = validation_service._extract_sign_features(frames)

        # Build diagnostics
        diagnostics = {}
        if quality_score < 0.5:
            diagnostics['quality_warning'] = 'Poor video quality detected'
        if detection_rate < 0.8:
            diagnostics['detection_warning'] = 'Inconsistent pose detection'

        return AnalyzeVideoResponse(
            success=True,
            video_url=request.video_url,
            frames_analyzed=len(frames),
            video_quality_score=quality_score,
            pose_detection_rate=detection_rate,
            extracted_features=features,
            diagnostics=diagnostics
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post("/compare-signs", response_model=CompareSignsResponse)
async def compare_signs(request: CompareSignsRequest):
    """
    Compare multiple videos of the same sign.

    Useful for:
    - Finding best video source for a sign
    - Analyzing variation in sign production
    - Quality comparison across datasets
    """
    try:
        results = []

        for video_url in request.video_urls:
            # Analyze each video
            pose_data = validation_service.pose_service.extract_pose_from_video(
                video_url,
                max_frames=request.max_frames
            )

            if pose_data.get('success', False):
                frames = pose_data.get('frames', [])
                quality = validation_service._assess_video_quality(frames)
                features = validation_service._extract_sign_features(frames)

                results.append({
                    'video_url': video_url,
                    'quality_score': quality,
                    'frame_count': len(frames),
                    'features': features
                })
            else:
                results.append({
                    'video_url': video_url,
                    'quality_score': 0.0,
                    'frame_count': 0,
                    'features': {},
                    'error': 'Failed to extract pose'
                })

        # Find best and worst
        valid_results = [r for r in results if r['quality_score'] > 0]
        if valid_results:
            best = max(valid_results, key=lambda r: r['quality_score'])
            worst = min(valid_results, key=lambda r: r['quality_score'])
            avg_quality = sum(r['quality_score'] for r in valid_results) / len(valid_results)
        else:
            best = None
            worst = None
            avg_quality = 0.0

        return CompareSignsResponse(
            gloss=request.gloss,
            total_videos=len(request.video_urls),
            comparison_results=results,
            best_video=best['video_url'] if best else None,
            worst_video=worst['video_url'] if worst else None,
            average_quality=avg_quality
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Comparison failed: {str(e)}"
        )


@router.get("/feature-definitions")
async def get_feature_definitions():
    """
    Get definitions of all ASL linguistic features.

    Returns available values for:
    - Handshapes
    - Locations
    - Movements
    - Palm orientations
    """
    return {
        "handshapes": {
            "description": "Standard ASL handshapes",
            "values": [h.value for h in Handshape]
        },
        "locations": {
            "description": "Locations in signing space",
            "values": [l.value for l in Location]
        },
        "movements": {
            "description": "Movement types",
            "values": [m.value for m in Movement]
        },
        "palm_orientations": {
            "description": "Palm facing directions",
            "values": [p.value for p in PalmOrientation]
        },
        "five_parameters": {
            "description": "The 5 parameters of ASL signs",
            "parameters": [
                "Handshape - What shape the hand makes",
                "Location - Where in signing space",
                "Movement - How the hand moves",
                "Palm Orientation - Direction palm faces",
                "Non-Manual Markers - Facial expressions and body language"
            ]
        }
    }


@router.get("/validation-metrics")
async def get_validation_metrics():
    """
    Get information about validation metrics and thresholds.

    Explains how signs are validated and what scores mean.
    """
    return {
        "confidence_thresholds": {
            "high": 0.85,
            "medium": 0.70,
            "low": 0.50,
            "description": "Overall confidence in sign interpretation"
        },
        "feature_weights": {
            "handshape": 0.30,
            "location": 0.25,
            "movement": 0.25,
            "palm_orientation": 0.20,
            "description": "Relative importance of each feature (may vary by sign)"
        },
        "video_quality_factors": {
            "pose_detection_rate": "Percentage of frames with valid pose",
            "hand_detection_rate": "Percentage of frames with hand landmarks",
            "landmark_visibility": "Average visibility score of landmarks",
            "threshold": 0.70
        },
        "validation_process": [
            "1. Extract pose landmarks from video using MediaPipe",
            "2. Analyze extracted features (handshape, location, movement, etc.)",
            "3. Compare with expected linguistic description",
            "4. Calculate confidence scores for each feature",
            "5. Generate overall validation result and diagnostics"
        ]
    }


@router.get("/test")
async def test_validation_service():
    """Test endpoint to verify validation service is operational"""
    return {
        "status": "operational",
        "service": "Sign Validation Service",
        "features": [
            "ASL 5-parameter framework",
            "MediaPipe pose extraction",
            "Feature-level validation",
            "Video quality assessment",
            "Diagnostic reporting",
            "Iterative framework refinement"
        ],
        "supported_parameters": {
            "handshapes": len(list(Handshape)),
            "locations": len(list(Location)),
            "movements": len(list(Movement)),
            "palm_orientations": len(list(PalmOrientation))
        }
    }
