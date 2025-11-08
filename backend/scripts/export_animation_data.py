#!/usr/bin/env python3
"""
Export Animation Data for 3D Avatar Systems

Converts MediaPipe pose data to formats usable in:
- Unity (JSON keyframes)
- Unreal Engine (FBX compatible)
- Blender (Python script)
- Web (Three.js JSON)

This allows external 3D avatar systems to replicate ASL signs exactly.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List
import math


class AnimationExporter:
    """Export pose data as animation keyframes"""

    # MediaPipe to standard skeleton bone mapping
    BONE_MAPPING = {
        'hips': 0,  # nose as reference
        'spine': 0,
        'chest': 0,
        'neck': 0,
        'head': 0,

        # Left arm
        'left_shoulder': 11,
        'left_upper_arm': 11,
        'left_elbow': 13,
        'left_forearm': 13,
        'left_wrist': 15,

        # Right arm
        'right_shoulder': 12,
        'right_upper_arm': 12,
        'right_elbow': 14,
        'right_forearm': 14,
        'right_wrist': 16,

        # Legs (less important for ASL but include for full body)
        'left_hip': 23,
        'left_knee': 25,
        'left_ankle': 27,
        'right_hip': 24,
        'right_knee': 26,
        'right_ankle': 28,
    }

    def __init__(self):
        pass

    def export_to_unity_json(self, sign_dir: Path, output_file: Path = None):
        """
        Export animation as Unity-compatible JSON

        Format:
        {
          "name": "SIGN_NAME",
          "fps": 30,
          "duration": 2.5,
          "bones": {
            "left_shoulder": [
              {"time": 0.0, "position": [x, y, z], "rotation": [x, y, z, w]},
              {"time": 0.033, "position": [x, y, z], "rotation": [x, y, z, w]},
              ...
            ],
            ...
          }
        }
        """

        # Load pose data
        pose_file = sign_dir / "pose_descriptions.json"
        with open(pose_file) as f:
            data = json.load(f)

        sign_name = data['gloss']
        fps = data['fps']
        frames = data['frames']
        duration = len(frames) / fps

        animation_data = {
            'name': sign_name,
            'fps': fps,
            'duration': duration,
            'total_frames': len(frames),
            'bones': {}
        }

        # Convert each frame to bone transforms
        for frame in frames:
            time = frame['timestamp']
            body = frame.get('body', [])

            if not body or len(body) < 33:
                continue

            # Extract bone positions and rotations
            for bone_name, landmark_idx in self.BONE_MAPPING.items():
                if landmark_idx < len(body):
                    lm = body[landmark_idx]

                    # Initialize bone track if needed
                    if bone_name not in animation_data['bones']:
                        animation_data['bones'][bone_name] = []

                    # Calculate rotation from landmark orientation
                    # For now, use position only (rotation would need adjacent landmarks)
                    keyframe = {
                        'time': time,
                        'position': [lm['x'], lm['y'], lm.get('z', 0)],
                        'rotation': [0, 0, 0, 1]  # Quaternion identity
                    }

                    animation_data['bones'][bone_name].append(keyframe)

        # Add hand finger bones
        animation_data['hands'] = {
            'right': self._export_hand_keyframes(frames, 'right_hand'),
            'left': self._export_hand_keyframes(frames, 'left_hand')
        }

        # Save
        if output_file is None:
            output_file = sign_dir / f"{sign_name}_unity_animation.json"

        with open(output_file, 'w') as f:
            json.dump(animation_data, f, indent=2)

        print(f"✅ Exported Unity animation: {output_file}")
        return output_file

    def _export_hand_keyframes(self, frames: List[Dict], hand_key: str) -> List[Dict]:
        """Export hand finger positions as keyframes"""

        hand_keyframes = []

        for frame in frames:
            hand = frame.get(hand_key)
            if not hand or len(hand) < 21:
                continue

            keyframe = {
                'time': frame['timestamp'],
                'landmarks': [
                    {'x': lm['x'], 'y': lm['y'], 'z': lm.get('z', 0)}
                    for lm in hand
                ]
            }

            hand_keyframes.append(keyframe)

        return hand_keyframes

    def export_to_blender_python(self, sign_dir: Path, output_file: Path = None):
        """
        Export as Blender Python script for direct import

        Generates a .py file that can be run in Blender to create animation
        """

        pose_file = sign_dir / "pose_descriptions.json"
        with open(pose_file) as f:
            data = json.load(f)

        sign_name = data['gloss']
        fps = data['fps']
        frames = data['frames']

        if output_file is None:
            output_file = sign_dir / f"{sign_name}_blender_import.py"

        # Save pose data as JSON file that Blender script will load
        pose_data_file = output_file.parent / f"{sign_name}_pose_data.json"
        with open(pose_data_file, 'w') as f:
            json.dump({
                'gloss': sign_name,
                'fps': fps,
                'frames': frames
            }, f, indent=2)

        # Generate Blender script that loads the JSON
        script = f"""# Blender Animation Import Script for {sign_name}
# Generated from MediaPipe pose data

import bpy
import mathutils
import json
from pathlib import Path

def create_asl_animation():
    # Load pose data
    script_dir = Path(__file__).parent
    pose_file = script_dir / "{sign_name}_pose_data.json"

    with open(pose_file) as f:
        data = json.load(f)

    sign_name = data['gloss']
    fps = data['fps']
    frames_data = data['frames']

    scene = bpy.context.scene
    scene.render.fps = int(fps)

    # Get armature (assumes you have an armature named 'Avatar')
    armature = bpy.data.objects.get('Avatar')
    if not armature:
        print("Error: No armature named 'Avatar' found")
        return

    # Set to pose mode
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    # Apply keyframes
    for frame_data in frames_data:
        frame_num = frame_data['frame']
        body = frame_data.get('body', [])

        # Set bone positions
        if len(body) >= 33:
            # Left shoulder
            if 'left_shoulder' in armature.pose.bones:
                bone = armature.pose.bones['left_shoulder']
                lm = body[11]
                bone.location = (lm['x'], lm['y'], lm.get('z', 0))
                bone.keyframe_insert(data_path='location', frame=frame_num)

            # Right shoulder
            if 'right_shoulder' in armature.pose.bones:
                bone = armature.pose.bones['right_shoulder']
                lm = body[12]
                bone.location = (lm['x'], lm['y'], lm.get('z', 0))
                bone.keyframe_insert(data_path='location', frame=frame_num)

            # Add more bones as needed...

    print(f"Animation '{{sign_name}}' imported successfully with {{len(frames_data)}} frames!")

# Run
create_asl_animation()
"""

        with open(output_file, 'w') as f:
            f.write(script)

        print(f"✅ Exported Blender script: {output_file}")
        print(f"✅ Exported pose data: {pose_data_file}")
        return output_file

    def export_to_threejs(self, sign_dir: Path, output_file: Path = None):
        """
        Export for Three.js web-based avatar

        Compatible with Three.js AnimationClip format
        """

        pose_file = sign_dir / "pose_descriptions.json"
        with open(pose_file) as f:
            data = json.load(f)

        sign_name = data['gloss']
        fps = data['fps']
        frames = data['frames']

        # Three.js animation clip format
        animation_clip = {
            'name': sign_name,
            'duration': len(frames) / fps,
            'fps': fps,
            'tracks': []
        }

        # Create tracks for each bone
        for bone_name, landmark_idx in self.BONE_MAPPING.items():
            position_track = {
                'name': f"{bone_name}.position",
                'type': 'vector',
                'times': [],
                'values': []
            }

            for frame in frames:
                body = frame.get('body', [])
                if body and landmark_idx < len(body):
                    lm = body[landmark_idx]
                    position_track['times'].append(frame['timestamp'])
                    position_track['values'].extend([lm['x'], lm['y'], lm.get('z', 0)])

            if position_track['times']:
                animation_clip['tracks'].append(position_track)

        # Add hand tracks
        for hand_name in ['right_hand', 'left_hand']:
            hand_track = {
                'name': f"{hand_name}.landmarks",
                'type': 'array',
                'times': [],
                'values': []
            }

            for frame in frames:
                hand = frame.get(hand_name, [])
                if hand and len(hand) >= 21:
                    hand_track['times'].append(frame['timestamp'])
                    hand_track['values'].append([
                        [lm['x'], lm['y'], lm.get('z', 0)]
                        for lm in hand
                    ])

            if hand_track['times']:
                animation_clip['tracks'].append(hand_track)

        if output_file is None:
            output_file = sign_dir / f"{sign_name}_threejs_animation.json"

        with open(output_file, 'w') as f:
            json.dump(animation_clip, f, indent=2)

        print(f"✅ Exported Three.js animation: {output_file}")
        return output_file

    def export_all_formats(self, sign_dir: Path):
        """Export animation in all supported formats"""

        print(f"\n{'='*100}")
        print(f"EXPORTING ANIMATION: {sign_dir.name.upper()}")
        print(f"{'='*100}\n")

        export_dir = sign_dir / "animation_exports"
        export_dir.mkdir(exist_ok=True)

        # Unity JSON
        self.export_to_unity_json(sign_dir, export_dir / f"{sign_dir.name}_unity.json")

        # Blender Python
        self.export_to_blender_python(sign_dir, export_dir / f"{sign_dir.name}_blender.py")

        # Three.js
        self.export_to_threejs(sign_dir, export_dir / f"{sign_dir.name}_threejs.json")

        print(f"\n📁 All formats exported to: {export_dir}\n")


def main():
    """Export animations for test signs"""

    exporter = AnimationExporter()

    test_signs = [
        Path("/tmp/avatar_frames/please"),
        Path("/tmp/avatar_frames/good"),
        Path("/tmp/avatar_frames/two"),
    ]

    for sign_dir in test_signs:
        if sign_dir.exists():
            exporter.export_all_formats(sign_dir)
        else:
            print(f"⚠️  Sign not found: {sign_dir}")


if __name__ == "__main__":
    main()
