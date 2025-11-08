"""
Avatar Animation API Endpoints
Converts pose data to avatar animations for Ready Player Me
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from app.services.avatar_animation import AvatarAnimationService
from app.services.pose_extraction import PoseExtractionService

router = APIRouter(prefix="/api/avatar")

# Initialize services
avatar_service = AvatarAnimationService()
pose_service = PoseExtractionService()


class AnimationRequest(BaseModel):
    """Request for converting pose data to avatar animation"""
    video_url: str
    max_frames: int = 30
    fps: float = 30.0
    smoothing: float = 0.3


class AnimationResponse(BaseModel):
    """Response with avatar animation data"""
    success: bool
    animation_clip: Optional[Dict] = None
    duration: float = 0.0
    frame_count: int = 0
    error: Optional[str] = None


class BoneRotationRequest(BaseModel):
    """Request for converting single frame to bone rotations"""
    frame_data: Dict


class BoneRotationResponse(BaseModel):
    """Response with bone rotation data"""
    success: bool
    bone_rotations: Dict
    bone_count: int


@router.post("/animate", response_model=AnimationResponse)
async def create_animation(request: AnimationRequest):
    """
    Create avatar animation from video URL.

    Steps:
    1. Extract pose data from video using MediaPipe
    2. Convert poses to bone rotations
    3. Create animation clip with smoothing
    4. Return Three.js compatible animation data

    Returns:
        Animation clip ready for Three.js AnimationClip
    """
    try:
        # Step 1: Extract pose data
        pose_data = pose_service.extract_pose_from_video(
            request.video_url,
            max_frames=request.max_frames
        )

        if not pose_data.get('success', False):
            return AnimationResponse(
                success=False,
                error="Failed to extract pose from video"
            )

        # Step 2: Convert to animation clip
        animation_clip = avatar_service.convert_to_animation_clip(
            pose_data,
            fps=request.fps
        )

        # Step 3: Apply smoothing
        if request.smoothing > 0:
            animation_clip = avatar_service.smooth_animation(
                animation_clip,
                smoothing_factor=request.smoothing
            )

        return AnimationResponse(
            success=True,
            animation_clip=animation_clip,
            duration=animation_clip['duration'],
            frame_count=len(pose_data.get('frames', []))
        )

    except Exception as e:
        return AnimationResponse(
            success=False,
            error=f"Animation creation failed: {str(e)}"
        )


@router.post("/bone-rotations", response_model=BoneRotationResponse)
async def get_bone_rotations(request: BoneRotationRequest):
    """
    Convert a single frame of pose data to bone rotations.

    Useful for real-time avatar control or frame-by-frame animation.

    Args:
        request: Frame data from MediaPipe

    Returns:
        Bone rotations for humanoid avatar rig
    """
    try:
        bone_rotations = avatar_service.map_pose_to_bones(request.frame_data)

        return BoneRotationResponse(
            success=True,
            bone_rotations=bone_rotations,
            bone_count=len(bone_rotations)
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to calculate bone rotations: {str(e)}"
        )


@router.get("/bone-mapping")
async def get_bone_mapping():
    """
    Get the bone mapping configuration.

    Returns standard humanoid bone names and their MediaPipe landmark indices.
    Useful for understanding the avatar rig structure.
    """
    return {
        "bone_mapping": avatar_service.BONE_MAPPING,
        "hand_bones": avatar_service.HAND_BONES,
        "description": "Mapping of Ready Player Me humanoid bones to MediaPipe landmarks"
    }


@router.get("/test")
async def test_avatar_service():
    """
    Test endpoint to verify avatar animation service is working.
    """
    return {
        "status": "operational",
        "service": "Avatar Animation Service",
        "supported_bones": list(avatar_service.BONE_MAPPING.keys()),
        "finger_count": len(avatar_service.HAND_BONES),
        "features": [
            "MediaPipe to bone rotation conversion",
            "Animation clip generation",
            "Smoothing and filtering",
            "Ready Player Me compatible"
        ]
    }
