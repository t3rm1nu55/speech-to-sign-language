#!/usr/bin/env python3
"""
Manual Pose Data Analysis
Inspect actual coordinate values to understand MediaPipe output
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.pose_extraction import PoseExtractionService
import json

def analyze_sign(gloss: str, video_url: str, max_frames: int = 10):
    """Manually analyze pose data for a sign"""

    print(f"\n{'='*80}")
    print(f"MANUAL ANALYSIS: {gloss}")
    print(f"{'='*80}\n")

    pose_service = PoseExtractionService()

    # Extract pose
    result = pose_service.extract_pose_from_video(video_url, max_frames=max_frames)

    if not result.get('success'):
        print(f"❌ Failed to extract pose")
        return

    frames = result.get('frames', [])
    print(f"✅ Extracted {len(frames)} frames\n")

    # Filter to active frames (wrist visibility > 0.65)
    active_frames = []
    for i, frame in enumerate(frames):
        pose = frame.get('pose')
        if pose and len(pose) > 16:
            left_wrist_vis = pose[15].get('visibility', 0) if len(pose) > 15 else 0
            right_wrist_vis = pose[16].get('visibility', 0) if len(pose) > 16 else 0

            if left_wrist_vis > 0.65 or right_wrist_vis > 0.65:
                active_frames.append((i, frame))

    print(f"Active frames (wrist visibility > 0.65): {len(active_frames)}\n")

    if not active_frames:
        print("❌ No active frames found")
        return

    # Pick middle frame for analysis
    mid_idx = len(active_frames) // 2
    frame_num, frame = active_frames[mid_idx]

    print(f"Analyzing frame {frame_num} (middle of active sequence)\n")

    pose = frame.get('pose')
    right_hand = frame.get('right_hand')
    left_hand = frame.get('left_hand')

    # =========================
    # POSE LANDMARKS ANALYSIS
    # =========================
    print("─" * 80)
    print("POSE LANDMARKS (Body)")
    print("─" * 80)

    if pose and len(pose) >= 33:
        # Key landmarks
        landmarks_to_check = {
            'nose': 0,
            'left_eye': 2,
            'right_eye': 5,
            'mouth': 10,
            'left_shoulder': 11,
            'right_shoulder': 12,
            'left_wrist': 15,
            'right_wrist': 16
        }

        for name, idx in landmarks_to_check.items():
            if len(pose) > idx:
                lm = pose[idx]
                print(f"{name:20s} → x={lm['x']:.3f}, y={lm['y']:.3f}, z={lm['z']:.3f}, vis={lm.get('visibility', 0):.3f}")

        # Calculate ranges
        print(f"\nY-coordinate ranges:")
        nose_y = pose[0]['y']
        eye_y = (pose[2]['y'] + pose[5]['y']) / 2 if len(pose) > 5 else None
        mouth_y = pose[10]['y'] if len(pose) > 10 else None
        shoulder_y = (pose[11]['y'] + pose[12]['y']) / 2 if len(pose) > 12 else None
        wrist_y = pose[16]['y'] if len(pose) > 16 else None

        print(f"  Eyes:      {eye_y:.3f}")
        print(f"  Nose:      {nose_y:.3f}")
        print(f"  Mouth:     {mouth_y:.3f}")
        print(f"  Shoulders: {shoulder_y:.3f}")
        print(f"  Wrist:     {wrist_y:.3f}")

        if shoulder_y and wrist_y:
            print(f"\n  Wrist below shoulders? {wrist_y > shoulder_y} (wrist_y={wrist_y:.3f} vs shoulder_y={shoulder_y:.3f})")

    # =========================
    # HAND LANDMARKS ANALYSIS
    # =========================
    print(f"\n{'─' * 80}")
    print("HAND LANDMARKS (Right Hand)")
    print("─" * 80)

    if right_hand and len(right_hand) >= 21:
        # Show all 21 landmarks
        wrist = right_hand[0]
        print(f"Wrist (0):  x={wrist['x']:.3f}, y={wrist['y']:.3f}, z={wrist['z']:.3f}")

        # Finger tips
        finger_tips = {
            'Thumb tip (4)': 4,
            'Index tip (8)': 8,
            'Middle tip (12)': 12,
            'Ring tip (16)': 16,
            'Pinky tip (20)': 20
        }

        print(f"\nFinger tips:")
        for name, idx in finger_tips.items():
            tip = right_hand[idx]
            dist_from_wrist = ((tip['x'] - wrist['x'])**2 +
                              (tip['y'] - wrist['y'])**2 +
                              (tip['z'] - wrist['z'])**2)**0.5
            print(f"  {name:20s} → x={tip['x']:.3f}, y={tip['y']:.3f}, z={tip['z']:.3f}, dist={dist_from_wrist:.3f}")

        # Finger extension analysis
        print(f"\nFinger extension analysis:")

        # Index finger
        index_tip = right_hand[8]
        index_pip = right_hand[6]
        index_mcp = right_hand[5]

        tip_dist = ((index_tip['x'] - wrist['x'])**2 +
                   (index_tip['y'] - wrist['y'])**2 +
                   (index_tip['z'] - wrist['z'])**2)**0.5
        mcp_dist = ((index_mcp['x'] - wrist['x'])**2 +
                   (index_mcp['y'] - wrist['y'])**2 +
                   (index_mcp['z'] - wrist['z'])**2)**0.5

        extension_ratio = tip_dist / max(mcp_dist, 0.01)
        print(f"  Index: tip_dist={tip_dist:.3f}, mcp_dist={mcp_dist:.3f}, ratio={extension_ratio:.3f}")
        print(f"         Extended? ratio > 1.3: {extension_ratio > 1.3}, ratio > 1.4: {extension_ratio > 1.4}")

        # Check all 5 fingers
        fingers = [
            ('Thumb', 4, 2),
            ('Index', 8, 5),
            ('Middle', 12, 9),
            ('Ring', 16, 13),
            ('Pinky', 20, 17)
        ]

        extended_count = 0
        print(f"\nAll fingers extension ratios:")
        for name, tip_idx, mcp_idx in fingers:
            tip = right_hand[tip_idx]
            mcp = right_hand[mcp_idx]

            tip_d = ((tip['x'] - wrist['x'])**2 +
                    (tip['y'] - wrist['y'])**2 +
                    (tip['z'] - wrist['z'])**2)**0.5
            mcp_d = ((mcp['x'] - wrist['x'])**2 +
                    (mcp['y'] - wrist['y'])**2 +
                    (mcp['z'] - wrist['z'])**2)**0.5

            ratio = tip_d / max(mcp_d, 0.01)
            extended = ratio > 1.3
            if extended:
                extended_count += 1

            print(f"  {name:8s}: ratio={ratio:.3f} {'✓ Extended' if extended else '✗ Curled'}")

        print(f"\nTotal extended: {extended_count}/5")

        # Finger spread (for FIVE vs B)
        if extended_count >= 4:
            index_tip = right_hand[8]
            middle_tip = right_hand[12]
            ring_tip = right_hand[16]
            pinky_tip = right_hand[20]

            def dist_3d(p1, p2):
                return ((p1['x']-p2['x'])**2 + (p1['y']-p2['y'])**2 + (p1['z']-p2['z'])**2)**0.5

            spread = (dist_3d(index_tip, middle_tip) +
                     dist_3d(middle_tip, ring_tip) +
                     dist_3d(ring_tip, pinky_tip)) / 3

            print(f"\nFinger spread: {spread:.3f}")
            print(f"  Fingers together (B)? spread < 0.04: {spread < 0.04}")
            print(f"  Fingers spread (5)? spread >= 0.04: {spread >= 0.04}")

    elif left_hand and len(left_hand) >= 21:
        print("(Using left hand - right hand not detected)")
        # Same analysis for left hand
    else:
        print("❌ No hand landmarks detected")

    # =========================
    # MOVEMENT ANALYSIS
    # =========================
    print(f"\n{'─' * 80}")
    print("MOVEMENT ANALYSIS")
    print("─" * 80)

    # Get wrist positions across all active frames
    wrist_positions = []
    for frame_num, f in active_frames:
        p = f.get('pose')
        if p and len(p) > 16:
            wrist = p[16]
            wrist_positions.append({
                'frame': frame_num,
                'x': wrist['x'],
                'y': wrist['y'],
                'z': wrist['z']
            })

    if len(wrist_positions) >= 2:
        start = wrist_positions[0]
        end = wrist_positions[-1]

        dx = end['x'] - start['x']
        dy = end['y'] - start['y']
        dz = end['z'] - start['z']

        total_dist = (dx**2 + dy**2 + dz**2)**0.5

        print(f"Start position: x={start['x']:.3f}, y={start['y']:.3f}, z={start['z']:.3f}")
        print(f"End position:   x={end['x']:.3f}, y={end['y']:.3f}, z={end['z']:.3f}")
        print(f"\nDisplacement: dx={dx:.3f}, dy={dy:.3f}, dz={dz:.3f}")
        print(f"Total distance: {total_dist:.3f}")

        # Calculate path length
        path_length = 0
        for i in range(1, len(wrist_positions)):
            prev = wrist_positions[i-1]
            curr = wrist_positions[i]
            segment = ((curr['x']-prev['x'])**2 + (curr['y']-prev['y'])**2 + (curr['z']-prev['z'])**2)**0.5
            path_length += segment

        print(f"Path length: {path_length:.3f}")

        if total_dist > 0.01:
            print(f"\nPrimary direction:")
            abs_dx = abs(dx)
            abs_dy = abs(dy)
            abs_dz = abs(dz)

            if abs_dy == max(abs_dx, abs_dy, abs_dz):
                direction = "UP" if dy < 0 else "DOWN"
                print(f"  Y-axis: {direction} (dy={dy:.3f})")
            elif abs_dx == max(abs_dx, abs_dy, abs_dz):
                direction = "RIGHT" if dx > 0 else "LEFT"
                print(f"  X-axis: {direction} (dx={dx:.3f})")
            elif abs_dz == max(abs_dx, abs_dy, abs_dz):
                direction = "FORWARD" if dz > 0 else "BACKWARD"
                print(f"  Z-axis: {direction} (dz={dz:.3f})")
        else:
            print(f"\nMinimal movement (NONE or CONTACT)")

        # Check for reversals
        velocities_y = []
        for i in range(1, len(wrist_positions)):
            prev = wrist_positions[i-1]
            curr = wrist_positions[i]
            velocities_y.append(curr['y'] - prev['y'])

        reversals = sum(1 for i in range(1, len(velocities_y))
                       if velocities_y[i] * velocities_y[i-1] < 0)

        print(f"\nDirection reversals (Y-axis): {reversals}")
        print(f"  Alternating? reversals >= 3: {reversals >= 3}")

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    # Analyze a few representative signs

    test_signs = [
        ("FATHER", "http://aslbricks.org/New/ASL-Videos/father.mp4"),  # Should be 5 handshape at forehead
        ("TWO", "http://aslbricks.org/New/ASL-Videos/two.mp4"),        # Should be 2 handshape
        ("PLEASE", "http://aslbricks.org/New/ASL-Videos/please.mp4"),  # Should be flat/B at chest, circular
        ("GOOD", "http://aslbricks.org/New/ASL-Videos/good.mp4"),      # Should be flat at mouth, down
    ]

    for gloss, video_url in test_signs:
        analyze_sign(gloss, video_url, max_frames=15)
        input("Press Enter to continue to next sign...")
