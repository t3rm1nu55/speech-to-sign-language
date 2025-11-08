"""
Visual Pose Analysis - Examine actual frames and pose data
Saves annotated frames and detailed landmark analysis
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import numpy as np
from app.services.pose_extraction import PoseExtractionService
from app.database import SessionLocal
from app.models.sign_dictionary import SignEntry
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_video_with_visuals(gloss: str, output_dir: str = "/tmp/pose_analysis"):
    """
    Analyze a video and save annotated frames for visual inspection
    """

    # Create output directory
    Path(output_dir).mkdir(exist_ok=True, parents=True)

    # Get video URL
    db = SessionLocal()
    entry = db.query(SignEntry).filter(
        SignEntry.gloss == gloss.upper(),
        SignEntry.video_url.like('%aslbricks%')
    ).first()

    if not entry:
        entry = db.query(SignEntry).filter(
            SignEntry.word == gloss.lower(),
            SignEntry.video_url.like('%aslbricks%')
        ).first()

    if not entry:
        print(f"❌ No ASL Bricks video found for {gloss}")
        db.close()
        return

    video_url = entry.video_url
    print(f"\n{'='*80}")
    print(f"VISUAL POSE ANALYSIS: {gloss}")
    print(f"{'='*80}")
    print(f"Video URL: {video_url}")
    print()

    # Initialize services
    pose_service = PoseExtractionService()

    # Download video first
    import tempfile
    temp_path = pose_service._download_video(video_url)

    if not temp_path:
        print("❌ Failed to download video")
        db.close()
        return

    print(f"✅ Video downloaded to: {temp_path}")

    # Open video with cv2
    cap = cv2.VideoCapture(temp_path)

    if not cap.isOpened():
        print("❌ Failed to open video")
        db.close()
        return

    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"Video properties:")
    print(f"  Resolution: {width}x{height}")
    print(f"  FPS: {fps:.2f}")
    print(f"  Total frames: {total_frames}")
    print()

    # Initialize MediaPipe
    import mediapipe as mp
    mp_holistic = mp.solutions.holistic
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles

    holistic = mp_holistic.Holistic(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    # Process frames
    frame_analyses = []
    frame_count = 0
    max_frames = 10

    print(f"Processing first {max_frames} frames...")
    print()

    while cap.isOpened() and frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break

        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process with MediaPipe
        results = holistic.process(frame_rgb)

        # Analyze this frame
        analysis = {
            'frame_number': frame_count,
            'has_pose': results.pose_landmarks is not None,
            'has_left_hand': results.left_hand_landmarks is not None,
            'has_right_hand': results.right_hand_landmarks is not None,
            'has_face': results.face_landmarks is not None,
        }

        if results.pose_landmarks:
            analysis['pose_landmarks_count'] = len(results.pose_landmarks.landmark)
            # Check visibility of key points
            landmarks = results.pose_landmarks.landmark
            analysis['wrist_visibility'] = {
                'left': landmarks[15].visibility if len(landmarks) > 15 else 0,
                'right': landmarks[16].visibility if len(landmarks) > 16 else 0
            }

        if results.left_hand_landmarks:
            analysis['left_hand_landmarks_count'] = len(results.left_hand_landmarks.landmark)

        if results.right_hand_landmarks:
            analysis['right_hand_landmarks_count'] = len(results.right_hand_landmarks.landmark)

        frame_analyses.append(analysis)

        # Create annotated frame
        annotated_frame = frame.copy()

        # Draw pose landmarks
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(
                annotated_frame,
                results.pose_landmarks,
                mp_holistic.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
            )

        # Draw hand landmarks
        if results.left_hand_landmarks:
            mp_drawing.draw_landmarks(
                annotated_frame,
                results.left_hand_landmarks,
                mp_holistic.HAND_CONNECTIONS,
                mp_drawing_styles.get_default_hand_landmarks_style(),
                mp_drawing_styles.get_default_hand_connections_style()
            )

        if results.right_hand_landmarks:
            mp_drawing.draw_landmarks(
                annotated_frame,
                results.right_hand_landmarks,
                mp_holistic.HAND_CONNECTIONS,
                mp_drawing_styles.get_default_hand_landmarks_style(),
                mp_drawing_styles.get_default_hand_connections_style()
            )

        # Draw face landmarks (simplified)
        if results.face_landmarks:
            mp_drawing.draw_landmarks(
                annotated_frame,
                results.face_landmarks,
                mp_holistic.FACEMESH_TESSELATION,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style()
            )

        # Add text overlay
        status_text = f"Frame {frame_count} | Pose:{'✓' if analysis['has_pose'] else '✗'} "
        status_text += f"L-Hand:{'✓' if analysis['has_left_hand'] else '✗'} "
        status_text += f"R-Hand:{'✓' if analysis['has_right_hand'] else '✗'}"

        cv2.putText(annotated_frame, status_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Save annotated frame
        frame_path = f"{output_dir}/{gloss}_frame_{frame_count:03d}.jpg"
        cv2.imwrite(frame_path, annotated_frame)

        # Also save original frame for comparison
        original_path = f"{output_dir}/{gloss}_original_{frame_count:03d}.jpg"
        cv2.imwrite(original_path, frame)

        frame_count += 1

    cap.release()
    holistic.close()

    # Print detailed analysis
    print(f"{'─'*80}")
    print(f"FRAME-BY-FRAME ANALYSIS:")
    print(f"{'─'*80}")

    for analysis in frame_analyses:
        frame_num = analysis['frame_number']
        pose = '✅' if analysis['has_pose'] else '❌'
        left = '✅' if analysis['has_left_hand'] else '❌'
        right = '✅' if analysis['has_right_hand'] else '❌'

        print(f"Frame {frame_num:2d}: Pose:{pose} L-Hand:{left} R-Hand:{right}", end='')

        if 'wrist_visibility' in analysis:
            l_vis = analysis['wrist_visibility']['left']
            r_vis = analysis['wrist_visibility']['right']
            print(f" | Wrist visibility L:{l_vis:.2f} R:{r_vis:.2f}", end='')

        print()

    # Summary statistics
    print(f"\n{'─'*80}")
    print(f"SUMMARY:")
    print(f"{'─'*80}")

    total = len(frame_analyses)
    pose_count = sum(1 for a in frame_analyses if a['has_pose'])
    left_count = sum(1 for a in frame_analyses if a['has_left_hand'])
    right_count = sum(1 for a in frame_analyses if a['has_right_hand'])

    print(f"Total frames processed: {total}")
    print(f"Pose detected: {pose_count}/{total} ({pose_count/total*100:.1f}%)")
    print(f"Left hand detected: {left_count}/{total} ({left_count/total*100:.1f}%)")
    print(f"Right hand detected: {right_count}/{total} ({right_count/total*100:.1f}%)")

    # Check wrist visibilities
    if any('wrist_visibility' in a for a in frame_analyses):
        left_vis = [a['wrist_visibility']['left'] for a in frame_analyses if 'wrist_visibility' in a]
        right_vis = [a['wrist_visibility']['right'] for a in frame_analyses if 'wrist_visibility' in a]

        if left_vis:
            print(f"\nAverage wrist visibility:")
            print(f"  Left wrist: {np.mean(left_vis):.3f} (range: {min(left_vis):.3f} - {max(left_vis):.3f})")
        if right_vis:
            print(f"  Right wrist: {np.mean(right_vis):.3f} (range: {min(right_vis):.3f} - {max(right_vis):.3f})")

    # Save analysis to JSON
    analysis_file = f"{output_dir}/{gloss}_analysis.json"
    with open(analysis_file, 'w') as f:
        json.dump({
            'gloss': gloss,
            'video_url': video_url,
            'video_properties': {
                'width': width,
                'height': height,
                'fps': fps,
                'total_frames': total_frames
            },
            'frames_analyzed': frame_analyses
        }, f, indent=2)

    print(f"\n{'─'*80}")
    print(f"OUTPUT FILES:")
    print(f"{'─'*80}")
    print(f"Annotated frames: {output_dir}/{gloss}_frame_*.jpg")
    print(f"Original frames: {output_dir}/{gloss}_original_*.jpg")
    print(f"Analysis data: {analysis_file}")

    print(f"\n💡 Open the annotated frames to see what MediaPipe detected!")
    print(f"   Compare with original frames to understand detection issues.")

    db.close()


def analyze_multiple_signs():
    """Analyze multiple signs for comparison"""

    signs = ["GOOD", "PLEASE", "SAD", "NEW"]

    print(f"{'='*80}")
    print(f"MULTI-SIGN VISUAL ANALYSIS")
    print(f"{'='*80}")
    print(f"Analyzing {len(signs)} signs to understand hand detection patterns")
    print()

    for sign in signs:
        analyze_video_with_visuals(sign)
        print("\n")


if __name__ == "__main__":
    import os
    if 'DATABASE_URL' not in os.environ:
        os.environ['DATABASE_URL'] = 'sqlite:///./sign_language.db'

    import sys
    if len(sys.argv) > 1:
        # Analyze specific sign
        analyze_video_with_visuals(sys.argv[1])
    else:
        # Analyze multiple signs
        analyze_multiple_signs()
