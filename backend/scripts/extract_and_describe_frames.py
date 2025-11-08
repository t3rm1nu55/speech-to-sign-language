#!/usr/bin/env python3
"""
Frame-by-Frame Avatar Pose Matching System

Extract frames from ASL videos, describe exact poses, and tune avatar to match
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.pose_extraction import PoseExtractionService
import cv2
import json
from pathlib import Path
from typing import Dict, List
import numpy as np

class FramePoseDescriber:
    """Extract and describe every frame for avatar matching"""

    def __init__(self, output_dir: str = "/tmp/avatar_frames"):
        self.pose_service = PoseExtractionService()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_all_frames(self, gloss: str, video_url: str):
        """Extract EVERY frame from video with pose data"""

        print(f"\n{'='*100}")
        print(f"EXTRACTING FRAMES FOR AVATAR MATCHING: {gloss}")
        print(f"{'='*100}\n")

        # Create sign-specific directory
        sign_dir = self.output_dir / gloss.lower()
        sign_dir.mkdir(exist_ok=True)

        # Download video
        print(f"Downloading video...")
        temp_path = self.pose_service._download_video(video_url)

        # Open video
        cap = cv2.VideoCapture(temp_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        print(f"Video: {fps:.2f} fps, {total_frames} frames")
        print(f"Extracting all frames...\n")

        # MediaPipe setup
        import mediapipe as mp
        mp_holistic = mp.solutions.holistic
        mp_drawing = mp.solutions.drawing_utils
        mp_drawing_styles = mp.solutions.drawing_styles

        holistic = mp_holistic.Holistic(
            static_image_mode=False,
            model_complexity=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        frame_descriptions = []
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # Convert to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Process with MediaPipe
            results = holistic.process(frame_rgb)

            # Create annotated frame
            annotated = frame.copy()

            # Draw all landmarks
            if results.pose_landmarks:
                mp_drawing.draw_landmarks(
                    annotated,
                    results.pose_landmarks,
                    mp_holistic.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
                )

            if results.left_hand_landmarks:
                mp_drawing.draw_landmarks(
                    annotated,
                    results.left_hand_landmarks,
                    mp_holistic.HAND_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing_styles.get_default_hand_landmarks_style()
                )

            if results.right_hand_landmarks:
                mp_drawing.draw_landmarks(
                    annotated,
                    results.right_hand_landmarks,
                    mp_holistic.HAND_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing_styles.get_default_hand_landmarks_style()
                )

            if results.face_landmarks:
                mp_drawing.draw_landmarks(
                    annotated,
                    results.face_landmarks,
                    mp_holistic.FACEMESH_CONTOURS,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_contours_style()
                )

            # Save original frame
            original_path = sign_dir / f"frame_{frame_count:04d}_original.jpg"
            cv2.imwrite(str(original_path), frame)

            # Save annotated frame
            annotated_path = sign_dir / f"frame_{frame_count:04d}_annotated.jpg"
            cv2.imwrite(str(annotated_path), annotated)

            # Extract pose description for avatar
            description = self._describe_pose_for_avatar(
                frame_count,
                results,
                frame.shape
            )

            frame_descriptions.append(description)

            if frame_count % 10 == 0:
                print(f"  Processed {frame_count}/{total_frames} frames...")

        cap.release()
        holistic.close()

        # Save all descriptions to JSON
        desc_file = sign_dir / "pose_descriptions.json"
        with open(desc_file, 'w') as f:
            json.dump({
                'gloss': gloss,
                'video_url': video_url,
                'fps': fps,
                'total_frames': frame_count,
                'frames': frame_descriptions
            }, f, indent=2)

        print(f"\n✅ Extracted {frame_count} frames to {sign_dir}")
        print(f"✅ Pose descriptions saved to {desc_file}")

        # Generate manual review file
        self._generate_review_file(gloss, frame_descriptions, sign_dir)

        return sign_dir

    def _describe_pose_for_avatar(self, frame_num: int, results, frame_shape) -> Dict:
        """Describe exact pose for avatar replication"""

        description = {
            'frame': frame_num,
            'timestamp': frame_num / 30.0,  # Assuming 30fps
            'body': None,
            'left_hand': None,
            'right_hand': None,
            'face': None
        }

        # Body pose (33 landmarks)
        if results.pose_landmarks:
            description['body'] = [
                {
                    'x': lm.x,
                    'y': lm.y,
                    'z': lm.z,
                    'visibility': lm.visibility
                }
                for lm in results.pose_landmarks.landmark
            ]

        # Left hand (21 landmarks)
        if results.left_hand_landmarks:
            description['left_hand'] = [
                {
                    'x': lm.x,
                    'y': lm.y,
                    'z': lm.z
                }
                for lm in results.left_hand_landmarks.landmark
            ]

        # Right hand (21 landmarks)
        if results.right_hand_landmarks:
            description['right_hand'] = [
                {
                    'x': lm.x,
                    'y': lm.y,
                    'z': lm.z
                }
                for lm in results.right_hand_landmarks.landmark
            ]

        # Face (468 landmarks - simplified to key points)
        if results.face_landmarks:
            # Just save key facial landmarks for expressions
            key_face_indices = [
                0, 1, 2, 3, 4, 5, 6,  # Face oval
                10, 152, 234, 454,  # Eyes
                61, 291, 199  # Mouth
            ]
            description['face'] = [
                {
                    'idx': idx,
                    'x': results.face_landmarks.landmark[idx].x,
                    'y': results.face_landmarks.landmark[idx].y,
                    'z': results.face_landmarks.landmark[idx].z
                }
                for idx in key_face_indices
                if idx < len(results.face_landmarks.landmark)
            ]

        return description

    def _generate_review_file(self, gloss: str, descriptions: List[Dict], sign_dir: Path):
        """Generate human-readable review file for manual avatar tuning"""

        review_file = sign_dir / "MANUAL_REVIEW.md"

        with open(review_file, 'w') as f:
            f.write(f"# Avatar Pose Matching Review: {gloss.upper()}\n\n")
            f.write(f"Total frames: {len(descriptions)}\n\n")
            f.write("## Instructions\n\n")
            f.write("For each frame below:\n")
            f.write("1. Look at the `frame_XXXX_original.jpg` image\n")
            f.write("2. Look at the `frame_XXXX_annotated.jpg` with MediaPipe overlay\n")
            f.write("3. Read the pose description\n")
            f.write("4. Adjust avatar parameters to match\n")
            f.write("5. Compare avatar output vs original - aim for 99% match\n")
            f.write("6. Note any discrepancies in the 'Avatar Match' section\n\n")
            f.write("---\n\n")

            # Sample every 5th frame for manual review (full dataset is in JSON)
            for i, desc in enumerate(descriptions):
                if i % 5 != 0:  # Review every 5th frame
                    continue

                frame_num = desc['frame']
                f.write(f"## Frame {frame_num}\n\n")
                f.write(f"**Time**: {desc['timestamp']:.2f}s\n\n")

                # Body pose summary
                if desc['body']:
                    f.write("### Body Pose\n\n")
                    body = desc['body']

                    # Key body points
                    nose = body[0]
                    left_shoulder = body[11]
                    right_shoulder = body[12]
                    left_wrist = body[15]
                    right_wrist = body[16]

                    f.write(f"- **Head**: x={nose['x']:.3f}, y={nose['y']:.3f}, z={nose['z']:.3f}\n")
                    f.write(f"- **Left shoulder**: x={left_shoulder['x']:.3f}, y={left_shoulder['y']:.3f}\n")
                    f.write(f"- **Right shoulder**: x={right_shoulder['x']:.3f}, y={right_shoulder['y']:.3f}\n")
                    f.write(f"- **Left wrist**: x={left_wrist['x']:.3f}, y={left_wrist['y']:.3f}, z={left_wrist['z']:.3f}, vis={left_wrist['visibility']:.2f}\n")
                    f.write(f"- **Right wrist**: x={right_wrist['x']:.3f}, y={right_wrist['y']:.3f}, z={right_wrist['z']:.3f}, vis={right_wrist['visibility']:.2f}\n\n")

                # Hand poses
                if desc['right_hand']:
                    f.write("### Right Hand\n\n")
                    hand = desc['right_hand']
                    wrist = hand[0]
                    thumb_tip = hand[4]
                    index_tip = hand[8]
                    middle_tip = hand[12]

                    f.write(f"- Wrist: x={wrist['x']:.3f}, y={wrist['y']:.3f}, z={wrist['z']:.3f}\n")
                    f.write(f"- Thumb tip: x={thumb_tip['x']:.3f}, y={thumb_tip['y']:.3f}\n")
                    f.write(f"- Index tip: x={index_tip['x']:.3f}, y={index_tip['y']:.3f}\n")
                    f.write(f"- Middle tip: x={middle_tip['x']:.3f}, y={middle_tip['y']:.3f}\n\n")

                if desc['left_hand']:
                    f.write("### Left Hand\n\n")
                    hand = desc['left_hand']
                    wrist = hand[0]
                    f.write(f"- Wrist: x={wrist['x']:.3f}, y={wrist['y']:.3f}, z={wrist['z']:.3f}\n\n")

                # Avatar matching section
                f.write("### Avatar Match Status\n\n")
                f.write("- [ ] Body pose matches (99%)\n")
                f.write("- [ ] Right hand matches (99%)\n")
                f.write("- [ ] Left hand matches (99%)\n")
                f.write("- [ ] Overall match achieved\n\n")
                f.write("**Notes**: _Add any discrepancies or adjustments needed_\n\n")
                f.write("---\n\n")

        print(f"✅ Manual review file generated: {review_file}")


def main():
    """Extract frames for all test signs"""

    describer = FramePoseDescriber()

    # Start with a few key signs - use correct ASL Bricks URLs
    test_signs = [
        ("PLEASE", "http://aslbricks.org/New/ASL-Videos/please.mp4"),
        ("GOOD", "http://aslbricks.org/New/ASL-Videos/good.mp4"),
        ("TWO", "http://aslbricks.org/New/ASL-Videos/two.mp4"),
    ]

    for gloss, video_url in test_signs:
        try:
            sign_dir = describer.extract_all_frames(gloss, video_url)
            print(f"\n📁 Output directory: {sign_dir}")
            print(f"   - Original frames: frame_XXXX_original.jpg")
            print(f"   - Annotated frames: frame_XXXX_annotated.jpg")
            print(f"   - Pose data: pose_descriptions.json")
            print(f"   - Manual review: MANUAL_REVIEW.md\n")
        except Exception as e:
            print(f"❌ Error processing {gloss}: {e}\n")
            continue


if __name__ == "__main__":
    main()
