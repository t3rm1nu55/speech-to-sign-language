"""
Avatar Animation Service
Converts MediaPipe pose data to Ready Player Me avatar bone rotations
"""

import numpy as np
from typing import Dict, List, Optional
import math


class AvatarAnimationService:
    """
    Service for converting MediaPipe pose landmarks to avatar animations.
    Supports Ready Player Me avatars with standard humanoid rig.
    """

    # Standard humanoid bone names (VRM/Ready Player Me compatible)
    BONE_MAPPING = {
        # Upper body
        'Hips': {'mediapipe_idx': 23, 'parent': None},
        'Spine': {'mediapipe_idx': 24, 'parent': 'Hips'},
        'Chest': {'mediapipe_idx': 12, 'parent': 'Spine'},
        'Neck': {'mediapipe_idx': 0, 'parent': 'Chest'},
        'Head': {'mediapipe_idx': 0, 'parent': 'Neck'},

        # Left arm
        'LeftShoulder': {'mediapipe_idx': 11, 'parent': 'Chest'},
        'LeftUpperArm': {'mediapipe_idx': 11, 'parent': 'LeftShoulder'},
        'LeftLowerArm': {'mediapipe_idx': 13, 'parent': 'LeftUpperArm'},
        'LeftHand': {'mediapipe_idx': 15, 'parent': 'LeftLowerArm'},

        # Right arm
        'RightShoulder': {'mediapipe_idx': 12, 'parent': 'Chest'},
        'RightUpperArm': {'mediapipe_idx': 12, 'parent': 'RightShoulder'},
        'RightLowerArm': {'mediapipe_idx': 14, 'parent': 'RightUpperArm'},
        'RightHand': {'mediapipe_idx': 16, 'parent': 'RightLowerArm'},
    }

    # Hand bone indices for finger mapping
    HAND_BONES = {
        'thumb': [1, 2, 3, 4],
        'index': [5, 6, 7, 8],
        'middle': [9, 10, 11, 12],
        'ring': [13, 14, 15, 16],
        'pinky': [17, 18, 19, 20]
    }

    def __init__(self):
        """Initialize avatar animation service"""
        pass

    def calculate_rotation(self, point_a: Dict, point_b: Dict, point_c: Optional[Dict] = None) -> Dict[str, float]:
        """
        Calculate rotation angles between three points (joint chain).

        Args:
            point_a: Parent joint position {x, y, z, visibility}
            point_b: Current joint position
            point_c: Child joint position (optional)

        Returns:
            Dict with rotation angles in degrees {x, y, z}
        """
        if point_c is None:
            # Two-point rotation (simple case)
            dx = point_b['x'] - point_a['x']
            dy = point_b['y'] - point_a['y']
            dz = point_b['z'] - point_a['z']

            # Calculate angles
            yaw = math.atan2(dy, dx) * 180 / math.pi
            pitch = math.atan2(dz, math.sqrt(dx*dx + dy*dy)) * 180 / math.pi

            return {'x': pitch, 'y': yaw, 'z': 0.0}

        # Three-point rotation (more accurate for joint chains)
        # Vector from A to B
        v1 = np.array([
            point_b['x'] - point_a['x'],
            point_b['y'] - point_a['y'],
            point_b['z'] - point_a['z']
        ])

        # Vector from B to C
        v2 = np.array([
            point_c['x'] - point_b['x'],
            point_c['y'] - point_b['y'],
            point_c['z'] - point_b['z']
        ])

        # Normalize vectors
        v1_norm = v1 / (np.linalg.norm(v1) + 1e-6)
        v2_norm = v2 / (np.linalg.norm(v2) + 1e-6)

        # Calculate rotation to align v1 with v2
        axis = np.cross(v1_norm, v2_norm)
        angle = np.arccos(np.clip(np.dot(v1_norm, v2_norm), -1.0, 1.0))

        if np.linalg.norm(axis) < 1e-6:
            return {'x': 0.0, 'y': 0.0, 'z': 0.0}

        axis = axis / np.linalg.norm(axis)

        # Convert to Euler angles (approximation)
        angle_deg = angle * 180 / math.pi

        return {
            'x': axis[0] * angle_deg,
            'y': axis[1] * angle_deg,
            'z': axis[2] * angle_deg
        }

    def map_pose_to_bones(self, frame_data: Dict) -> Dict[str, Dict]:
        """
        Convert MediaPipe pose landmarks to avatar bone rotations.

        Args:
            frame_data: Single frame from MediaPipe with pose, left_hand, right_hand

        Returns:
            Dict mapping bone names to rotation data
        """
        bone_rotations = {}
        pose = frame_data.get('pose', [])

        if not pose or len(pose) < 33:
            return bone_rotations

        # Calculate upper body rotations
        # Shoulders
        if pose[11]['visibility'] > 0.5 and pose[12]['visibility'] > 0.5:
            shoulder_center = {
                'x': (pose[11]['x'] + pose[12]['x']) / 2,
                'y': (pose[11]['y'] + pose[12]['y']) / 2,
                'z': (pose[11]['z'] + pose[12]['z']) / 2,
                'visibility': 1.0
            }

            # Spine rotation
            if pose[23]['visibility'] > 0.5 and pose[24]['visibility'] > 0.5:
                hip_center = {
                    'x': (pose[23]['x'] + pose[24]['x']) / 2,
                    'y': (pose[23]['y'] + pose[24]['y']) / 2,
                    'z': (pose[23]['z'] + pose[24]['z']) / 2,
                    'visibility': 1.0
                }
                bone_rotations['Spine'] = self.calculate_rotation(hip_center, shoulder_center)

        # Left arm
        if (pose[11]['visibility'] > 0.5 and
            pose[13]['visibility'] > 0.5 and
            pose[15]['visibility'] > 0.5):
            bone_rotations['LeftUpperArm'] = self.calculate_rotation(
                pose[11], pose[13], pose[15]
            )
            bone_rotations['LeftLowerArm'] = self.calculate_rotation(
                pose[13], pose[15]
            )

        # Right arm
        if (pose[12]['visibility'] > 0.5 and
            pose[14]['visibility'] > 0.5 and
            pose[16]['visibility'] > 0.5):
            bone_rotations['RightUpperArm'] = self.calculate_rotation(
                pose[12], pose[14], pose[16]
            )
            bone_rotations['RightLowerArm'] = self.calculate_rotation(
                pose[14], pose[16]
            )

        # Add hand rotations if available
        left_hand = frame_data.get('left_hand', [])
        right_hand = frame_data.get('right_hand', [])

        if left_hand and len(left_hand) >= 21:
            bone_rotations['LeftHand'] = self.calculate_hand_rotation(left_hand)
            bone_rotations['LeftFingers'] = self.map_finger_rotations(left_hand)

        if right_hand and len(right_hand) >= 21:
            bone_rotations['RightHand'] = self.calculate_hand_rotation(right_hand)
            bone_rotations['RightFingers'] = self.map_finger_rotations(right_hand)

        return bone_rotations

    def calculate_hand_rotation(self, hand_landmarks: List[Dict]) -> Dict[str, float]:
        """
        Calculate overall hand rotation from wrist and palm landmarks.

        Args:
            hand_landmarks: 21 hand landmarks from MediaPipe

        Returns:
            Rotation angles {x, y, z}
        """
        if len(hand_landmarks) < 21:
            return {'x': 0.0, 'y': 0.0, 'z': 0.0}

        # Use wrist (0), middle finger base (9), and pinky base (17)
        wrist = hand_landmarks[0]
        middle_base = hand_landmarks[9]
        pinky_base = hand_landmarks[17]

        return self.calculate_rotation(wrist, middle_base, pinky_base)

    def map_finger_rotations(self, hand_landmarks: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Calculate rotation for each finger joint.

        Args:
            hand_landmarks: 21 hand landmarks from MediaPipe

        Returns:
            Dict mapping finger names to joint rotations
        """
        finger_rotations = {}

        for finger_name, indices in self.HAND_BONES.items():
            joints = []
            for i in range(len(indices) - 1):
                idx_a = indices[i]
                idx_b = indices[i + 1]

                if (idx_a < len(hand_landmarks) and
                    idx_b < len(hand_landmarks) and
                    hand_landmarks[idx_a]['visibility'] > 0.5 and
                    hand_landmarks[idx_b]['visibility'] > 0.5):

                    rotation = self.calculate_rotation(
                        hand_landmarks[idx_a],
                        hand_landmarks[idx_b]
                    )
                    joints.append({
                        'joint': i,
                        'rotation': rotation
                    })

            finger_rotations[finger_name] = joints

        return finger_rotations

    def convert_to_animation_clip(self, pose_data: Dict, fps: float = 30.0) -> Dict:
        """
        Convert multiple frames of pose data to animation clip format.

        Args:
            pose_data: Full pose extraction result with frames array
            fps: Target frames per second

        Returns:
            Animation clip data compatible with Three.js AnimationClip
        """
        frames = pose_data.get('frames', [])
        if not frames:
            return {'tracks': [], 'duration': 0.0}

        # Build tracks for each bone
        bone_tracks = {}

        for frame_idx, frame in enumerate(frames):
            bone_rotations = self.map_pose_to_bones(frame)

            for bone_name, rotation in bone_rotations.items():
                if bone_name not in bone_tracks:
                    bone_tracks[bone_name] = {
                        'times': [],
                        'rotations': []
                    }

                time = frame_idx / fps
                bone_tracks[bone_name]['times'].append(time)

                # Convert to quaternion (simplified - using Euler for now)
                bone_tracks[bone_name]['rotations'].append(rotation)

        # Build Three.js compatible track format
        tracks = []
        for bone_name, track_data in bone_tracks.items():
            tracks.append({
                'name': f'{bone_name}.rotation',
                'times': track_data['times'],
                'values': track_data['rotations']
            })

        duration = len(frames) / fps if frames else 0.0

        return {
            'name': 'ASL_Sign_Animation',
            'duration': duration,
            'fps': fps,
            'tracks': tracks
        }

    def smooth_animation(self, animation_clip: Dict, smoothing_factor: float = 0.3) -> Dict:
        """
        Apply smoothing to animation tracks to reduce jitter.

        Args:
            animation_clip: Animation clip data
            smoothing_factor: 0.0 (no smoothing) to 1.0 (maximum smoothing)

        Returns:
            Smoothed animation clip
        """
        smoothed_tracks = []

        for track in animation_clip.get('tracks', []):
            values = track['values']
            if len(values) < 3:
                smoothed_tracks.append(track)
                continue

            smoothed_values = [values[0]]  # Keep first value

            for i in range(1, len(values) - 1):
                prev_val = values[i - 1]
                curr_val = values[i]
                next_val = values[i + 1]

                # Apply weighted average
                smoothed = {
                    'x': (prev_val['x'] * smoothing_factor +
                          curr_val['x'] * (1 - 2 * smoothing_factor) +
                          next_val['x'] * smoothing_factor),
                    'y': (prev_val['y'] * smoothing_factor +
                          curr_val['y'] * (1 - 2 * smoothing_factor) +
                          next_val['y'] * smoothing_factor),
                    'z': (prev_val['z'] * smoothing_factor +
                          curr_val['z'] * (1 - 2 * smoothing_factor) +
                          next_val['z'] * smoothing_factor)
                }
                smoothed_values.append(smoothed)

            smoothed_values.append(values[-1])  # Keep last value

            smoothed_tracks.append({
                'name': track['name'],
                'times': track['times'],
                'values': smoothed_values
            })

        return {
            'name': animation_clip['name'],
            'duration': animation_clip['duration'],
            'fps': animation_clip['fps'],
            'tracks': smoothed_tracks
        }
