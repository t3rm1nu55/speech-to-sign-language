#!/usr/bin/env python3
"""
Avatar Rendering System - Replicate ASL signs from pose data

Takes MediaPipe pose coordinates and renders a stick figure avatar
that matches the exact pose. Goal: 99% visual similarity.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from pathlib import Path
import cv2
from typing import Dict, List, Tuple

class AvatarRenderer:
    """Renders avatar from MediaPipe pose coordinates"""

    def __init__(self):
        # MediaPipe Pose connections (33 body landmarks)
        self.POSE_CONNECTIONS = [
            # Face
            (0, 1), (1, 2), (2, 3), (3, 7),  # Left face
            (0, 4), (4, 5), (5, 6), (6, 8),  # Right face
            # Torso
            (9, 10),  # Mouth
            (11, 12),  # Shoulders
            (11, 23), (12, 24),  # Shoulder to hip
            (23, 24),  # Hips
            # Arms
            (11, 13), (13, 15),  # Left arm
            (12, 14), (14, 16),  # Right arm
            # Legs
            (23, 25), (25, 27), (27, 29), (29, 31),  # Left leg
            (24, 26), (26, 28), (28, 30), (30, 32),  # Right leg
        ]

        # Hand connections (21 landmarks each)
        self.HAND_CONNECTIONS = [
            # Thumb
            (0, 1), (1, 2), (2, 3), (3, 4),
            # Index
            (0, 5), (5, 6), (6, 7), (7, 8),
            # Middle
            (0, 9), (9, 10), (10, 11), (11, 12),
            # Ring
            (0, 13), (13, 14), (14, 15), (15, 16),
            # Pinky
            (0, 17), (17, 18), (18, 19), (19, 20),
        ]

    def load_pose_frame(self, json_file: Path, frame_number: int) -> Dict:
        """Load pose data for specific frame"""
        with open(json_file) as f:
            data = json.load(f)

        for frame in data['frames']:
            if frame['frame'] == frame_number:
                return frame

        raise ValueError(f"Frame {frame_number} not found in {json_file}")

    def render_avatar(self, pose_data: Dict, output_path: str = None, show_original: bool = False):
        """
        Render avatar from pose data

        Args:
            pose_data: Frame data with body/hand/face landmarks
            output_path: Where to save rendered image
            show_original: If True, show original video frame side-by-side
        """

        fig, axes = plt.subplots(1, 2 if show_original else 1, figsize=(12 if show_original else 6, 6))
        if not show_original:
            axes = [axes]

        ax = axes[0]
        ax.set_xlim(0, 1)
        ax.set_ylim(1, 0)  # Invert Y for image coordinates
        ax.set_aspect('equal')
        ax.set_title(f"Avatar Render - Frame {pose_data['frame']}")

        # Draw body
        if pose_data['body']:
            self._draw_body(ax, pose_data['body'])

        # Draw right hand
        if pose_data['right_hand']:
            self._draw_hand(ax, pose_data['right_hand'], color='red', label='Right')

        # Draw left hand
        if pose_data['left_hand']:
            self._draw_hand(ax, pose_data['left_hand'], color='blue', label='Left')

        ax.legend()
        ax.grid(True, alpha=0.3)

        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            print(f"Saved avatar render to: {output_path}")

        plt.close()

    def _draw_body(self, ax, body_landmarks: List[Dict]):
        """Draw body skeleton"""

        # Draw connections
        for conn in self.POSE_CONNECTIONS:
            start_idx, end_idx = conn
            if start_idx < len(body_landmarks) and end_idx < len(body_landmarks):
                start = body_landmarks[start_idx]
                end = body_landmarks[end_idx]

                # Only draw if both landmarks are visible
                if start.get('visibility', 0) > 0.5 and end.get('visibility', 0) > 0.5:
                    ax.plot(
                        [start['x'], end['x']],
                        [start['y'], end['y']],
                        'g-', linewidth=2, alpha=0.7
                    )

        # Draw joints
        for i, lm in enumerate(body_landmarks):
            if lm.get('visibility', 0) > 0.5:
                ax.plot(lm['x'], lm['y'], 'go', markersize=4)

    def _draw_hand(self, ax, hand_landmarks: List[Dict], color='red', label='Hand'):
        """Draw hand skeleton"""

        # Draw connections
        for conn in self.HAND_CONNECTIONS:
            start_idx, end_idx = conn
            if start_idx < len(hand_landmarks) and end_idx < len(hand_landmarks):
                start = hand_landmarks[start_idx]
                end = hand_landmarks[end_idx]

                ax.plot(
                    [start['x'], end['x']],
                    [start['y'], end['y']],
                    color=color, linewidth=1.5, alpha=0.7
                )

        # Draw joints
        for i, lm in enumerate(hand_landmarks):
            ax.plot(lm['x'], lm['y'], 'o', color=color, markersize=3, label=label if i == 0 else '')

    def render_comparison(self, sign_dir: Path, frame_number: int, output_dir: Path = None):
        """
        Render avatar and compare with original frame side-by-side

        Args:
            sign_dir: Directory with extracted frames
            frame_number: Which frame to render
            output_dir: Where to save comparison
        """

        # Load pose data
        pose_file = sign_dir / "pose_descriptions.json"
        pose_data = self.load_pose_frame(pose_file, frame_number)

        # Load original and annotated frames
        original_img = cv2.imread(str(sign_dir / f"frame_{frame_number:04d}_original.jpg"))
        annotated_img = cv2.imread(str(sign_dir / f"frame_{frame_number:04d}_annotated.jpg"))

        if original_img is None or annotated_img is None:
            raise FileNotFoundError(f"Frame {frame_number} images not found")

        original_img = cv2.cvtColor(original_img, cv2.COLOR_BGR2RGB)
        annotated_img = cv2.cvtColor(annotated_img, cv2.COLOR_BGR2RGB)

        # Create comparison figure
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))

        # Original video frame
        axes[0].imshow(original_img)
        axes[0].set_title(f"Original Frame {frame_number}")
        axes[0].axis('off')

        # MediaPipe annotated
        axes[1].imshow(annotated_img)
        axes[1].set_title("MediaPipe Skeleton")
        axes[1].axis('off')

        # Avatar render
        ax = axes[2]
        ax.set_xlim(0, 1)
        ax.set_ylim(1, 0)
        ax.set_aspect('equal')
        ax.set_title("Avatar Render")

        # Draw avatar
        if pose_data['body']:
            self._draw_body(ax, pose_data['body'])
        if pose_data['right_hand']:
            self._draw_hand(ax, pose_data['right_hand'], color='red', label='Right')
        if pose_data['left_hand']:
            self._draw_hand(ax, pose_data['left_hand'], color='blue', label='Left')

        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"comparison_frame_{frame_number:04d}.jpg"
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            print(f"Saved comparison to: {output_file}")

        plt.close()

        return original_img, annotated_img

    def batch_render_sign(self, sign_dir: Path, sample_every: int = 5):
        """
        Render multiple frames from a sign for review

        Args:
            sign_dir: Directory with sign data
            sample_every: Render every Nth frame
        """

        print(f"\n{'='*100}")
        print(f"RENDERING SIGN: {sign_dir.name.upper()}")
        print(f"{'='*100}\n")

        # Load pose descriptions
        pose_file = sign_dir / "pose_descriptions.json"
        with open(pose_file) as f:
            data = json.load(f)

        total_frames = data['total_frames']
        frames_to_render = list(range(1, total_frames + 1, sample_every))

        print(f"Total frames: {total_frames}")
        print(f"Rendering {len(frames_to_render)} frames (every {sample_every})\n")

        output_dir = sign_dir / "avatar_renders"
        output_dir.mkdir(exist_ok=True)

        for frame_num in frames_to_render:
            try:
                self.render_comparison(sign_dir, frame_num, output_dir)
                print(f"  ✓ Frame {frame_num}")
            except Exception as e:
                print(f"  ✗ Frame {frame_num}: {e}")

        print(f"\n✅ Rendered {len(frames_to_render)} comparison images")
        print(f"📁 Output: {output_dir}\n")


def main():
    """Test avatar rendering"""

    renderer = AvatarRenderer()

    # Test with extracted signs
    test_signs = [
        "/tmp/avatar_frames/please",
        "/tmp/avatar_frames/good",
        "/tmp/avatar_frames/two",
    ]

    for sign_path in test_signs:
        sign_dir = Path(sign_path)
        if sign_dir.exists():
            renderer.batch_render_sign(sign_dir, sample_every=10)
        else:
            print(f"⚠️  Sign not found: {sign_path}")


if __name__ == "__main__":
    main()
