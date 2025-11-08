"""
Pose Extraction Service using MediaPipe
Extracts skeleton data from ASL sign videos for visualization
"""

import cv2
import json
import logging
import numpy as np
from typing import Dict, List, Any, Optional
from pathlib import Path
import requests
from io import BytesIO

logger = logging.getLogger(__name__)


class PoseExtractionService:
    """Extract pose data from videos using MediaPipe"""

    def __init__(self):
        self.mp_holistic = None
        self.holistic = None
        self._initialize_mediapipe()

    def _initialize_mediapipe(self):
        """Lazy initialize MediaPipe"""
        try:
            import mediapipe as mp
            self.mp_holistic = mp.solutions.holistic
            self.holistic = self.mp_holistic.Holistic(
                static_image_mode=False,
                model_complexity=1,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            logger.info("MediaPipe initialized successfully")
        except ImportError:
            logger.error("MediaPipe not installed. Install with: pip install mediapipe opencv-python")
            raise

    def extract_pose_from_video(self, video_source: str, max_frames: int = 30) -> Dict[str, Any]:
        """
        Extract pose landmarks from video

        Args:
            video_source: Path to video file or URL
            max_frames: Maximum number of frames to process

        Returns:
            Dictionary with pose data for each frame
        """
        if not self.holistic:
            raise RuntimeError("MediaPipe not initialized")

        # Download video if URL
        if video_source.startswith('http'):
            video_path = self._download_video(video_source)
            if not video_path:
                return {
                    "success": False,
                    "error": "Failed to download video",
                    "frames": [],
                    "fps": 0,
                    "total_frames": 0,
                    "processed_frames": 0
                }
            cap = cv2.VideoCapture(video_path)
        else:
            cap = cv2.VideoCapture(video_source)

        if not cap.isOpened():
            logger.error(f"Failed to open video: {video_source}")
            return {
                "success": False,
                "error": "Failed to open video",
                "frames": [],
                "fps": 0,
                "total_frames": 0,
                "processed_frames": 0
            }

        frames_data = []
        frame_count = 0
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        logger.info(f"Processing video: {fps} fps, {total_frames} total frames")

        while cap.isOpened() and frame_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Process with MediaPipe
            results = self.holistic.process(frame_rgb)

            # Extract landmarks
            frame_data = self._extract_landmarks(results, frame_count)
            if frame_data:
                frames_data.append(frame_data)

            frame_count += 1

        cap.release()

        # Determine success
        success = len(frames_data) > 0

        return {
            "success": success,
            "fps": fps,
            "total_frames": total_frames,
            "processed_frames": frame_count,
            "frames": frames_data
        }

    def _download_video(self, url: str, timeout: int = 30) -> Optional[str]:
        """
        Download video from URL to temporary location

        Uses yt-dlp for YouTube/streaming sites, requests for direct URLs
        """
        import tempfile
        import os

        temp_path = f"/tmp/video_{abs(hash(url))}.mp4"

        # Try yt-dlp first for YouTube and other streaming sites
        if 'youtube.com' in url or 'youtu.be' in url or 'vimeo.com' in url:
            try:
                import yt_dlp

                ydl_opts = {
                    'format': 'best[ext=mp4]/best',
                    'outtmpl': temp_path,
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'socket_timeout': timeout,
                }

                logger.info(f"Downloading with yt-dlp: {url}")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                if os.path.exists(temp_path):
                    logger.info(f"Downloaded video to {temp_path}")
                    return temp_path
                else:
                    logger.error("yt-dlp download completed but file not found")
                    return None

            except ImportError:
                logger.warning("yt-dlp not installed, falling back to requests")
            except Exception as e:
                logger.error(f"yt-dlp download failed: {str(e)}")
                # Fall through to try requests

        # Fall back to requests for direct video URLs
        try:
            logger.info(f"Downloading with requests: {url}")
            response = requests.get(url, timeout=timeout, stream=True)
            if response.status_code == 200:
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"Downloaded video to {temp_path}")
                return temp_path
            else:
                logger.error(f"Failed to download video: HTTP {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            return None

    def _extract_landmarks(self, results, frame_number: int) -> Optional[Dict[str, Any]]:
        """Extract all landmarks from MediaPipe results"""
        if not results:
            return None

        frame_data = {
            "frame": frame_number,
            "pose": None,
            "left_hand": None,
            "right_hand": None,
            "face": None
        }

        # Extract pose landmarks (33 points)
        if results.pose_landmarks:
            frame_data["pose"] = self._landmarks_to_array(results.pose_landmarks.landmark)

        # Extract left hand landmarks (21 points)
        if results.left_hand_landmarks:
            frame_data["left_hand"] = self._landmarks_to_array(results.left_hand_landmarks.landmark)

        # Extract right hand landmarks (21 points)
        if results.right_hand_landmarks:
            frame_data["right_hand"] = self._landmarks_to_array(results.right_hand_landmarks.landmark)

        # Extract face landmarks (468 points - we'll use a subset)
        if results.face_landmarks:
            # Only extract key facial points (eyes, mouth, etc.)
            face_points = self._landmarks_to_array(results.face_landmarks.landmark)
            # Select key points (indices for eyes, nose, mouth)
            key_indices = [33, 133, 362, 263, 61, 291]  # Left eye, right eye, nose, mouth corners
            frame_data["face"] = [face_points[i] for i in key_indices if i < len(face_points)]

        return frame_data

    def _landmarks_to_array(self, landmarks) -> List[Dict[str, float]]:
        """Convert MediaPipe landmarks to array of coordinates"""
        return [
            {
                "x": landmark.x,
                "y": landmark.y,
                "z": landmark.z,
                "visibility": getattr(landmark, 'visibility', 1.0)
            }
            for landmark in landmarks
        ]

    def extract_pose_from_url(self, video_url: str) -> Dict[str, Any]:
        """
        Extract pose from video URL (convenience method)

        Args:
            video_url: URL to video file

        Returns:
            Pose data dictionary
        """
        return self.extract_pose_from_video(video_url, max_frames=30)

    def save_pose_data(self, pose_data: Dict[str, Any], output_path: str):
        """Save extracted pose data to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(pose_data, f, indent=2)
        logger.info(f"Pose data saved to {output_path}")

    def get_skeleton_connections(self) -> Dict[str, List[tuple]]:
        """
        Get skeleton connection definitions for visualization

        Returns:
            Dictionary of connection pairs for each body part
        """
        return {
            "pose": [
                # Torso
                (11, 12), (11, 23), (12, 24), (23, 24),
                # Left arm
                (11, 13), (13, 15), (15, 17), (15, 19), (15, 21),
                # Right arm
                (12, 14), (14, 16), (16, 18), (16, 20), (16, 22),
                # Left leg
                (23, 25), (25, 27), (27, 29), (27, 31),
                # Right leg
                (24, 26), (26, 28), (28, 30), (28, 32),
                # Face
                (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8)
            ],
            "left_hand": [
                # Thumb
                (0, 1), (1, 2), (2, 3), (3, 4),
                # Index
                (0, 5), (5, 6), (6, 7), (7, 8),
                # Middle
                (0, 9), (9, 10), (10, 11), (11, 12),
                # Ring
                (0, 13), (13, 14), (14, 15), (15, 16),
                # Pinky
                (0, 17), (17, 18), (18, 19), (19, 20)
            ],
            "right_hand": [
                # Same as left hand
                (0, 1), (1, 2), (2, 3), (3, 4),
                (0, 5), (5, 6), (6, 7), (7, 8),
                (0, 9), (9, 10), (10, 11), (11, 12),
                (0, 13), (13, 14), (14, 15), (15, 16),
                (0, 17), (17, 18), (18, 19), (19, 20)
            ]
        }


def create_pose_extraction_service() -> PoseExtractionService:
    """Factory function to create pose extraction service"""
    return PoseExtractionService()
