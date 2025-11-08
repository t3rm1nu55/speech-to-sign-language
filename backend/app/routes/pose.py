"""
API endpoints for pose extraction and skeleton visualization
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
import logging

from app.services.pose_extraction import create_pose_extraction_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pose", tags=["pose"])


class PoseExtractionRequest(BaseModel):
    """Request model for pose extraction"""
    video_url: str
    max_frames: Optional[int] = 30


class PoseExtractionResponse(BaseModel):
    """Response model for pose extraction"""
    success: bool
    fps: Optional[float] = None
    total_frames: Optional[int] = None
    processed_frames: Optional[int] = None
    frames: list
    skeleton_connections: Optional[dict] = None
    error: Optional[str] = None


@router.post("/extract", response_model=PoseExtractionResponse)
async def extract_pose(request: PoseExtractionRequest):
    """
    Extract pose data from video URL

    Extracts skeleton keypoints using MediaPipe Holistic:
    - 33 body pose landmarks
    - 21 hand landmarks per hand
    - Key facial landmarks

    Returns pose data suitable for skeleton visualization
    """
    try:
        pose_service = create_pose_extraction_service()

        logger.info(f"Extracting pose from: {request.video_url}")
        pose_data = pose_service.extract_pose_from_video(
            request.video_url,
            max_frames=request.max_frames
        )

        if "error" in pose_data:
            return PoseExtractionResponse(
                success=False,
                frames=[],
                error=pose_data["error"]
            )

        # Get skeleton connections for visualization
        connections = pose_service.get_skeleton_connections()

        return PoseExtractionResponse(
            success=True,
            fps=pose_data.get("fps"),
            total_frames=pose_data.get("total_frames"),
            processed_frames=pose_data.get("processed_frames"),
            frames=pose_data.get("frames", []),
            skeleton_connections=connections
        )

    except Exception as e:
        logger.error(f"Error extracting pose: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections")
async def get_skeleton_connections():
    """
    Get skeleton connection definitions for visualization

    Returns the bone/connection pairs that define how to draw
    the skeleton from the pose landmarks
    """
    try:
        pose_service = create_pose_extraction_service()
        connections = pose_service.get_skeleton_connections()

        return {
            "success": True,
            "connections": connections
        }

    except Exception as e:
        logger.error(f"Error getting connections: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test")
async def test_pose_extraction(video_url: str = Query(..., description="Video URL to test")):
    """
    Test endpoint for quick pose extraction

    Query params:
    - video_url: URL of video to process
    """
    try:
        pose_service = create_pose_extraction_service()
        pose_data = pose_service.extract_pose_from_url(video_url)

        return {
            "success": True,
            "data": pose_data,
            "summary": {
                "fps": pose_data.get("fps"),
                "frames_processed": pose_data.get("processed_frames"),
                "has_pose": any(f.get("pose") for f in pose_data.get("frames", [])),
                "has_hands": any(f.get("left_hand") or f.get("right_hand") for f in pose_data.get("frames", []))
            }
        }

    except Exception as e:
        logger.error(f"Error in test extraction: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
