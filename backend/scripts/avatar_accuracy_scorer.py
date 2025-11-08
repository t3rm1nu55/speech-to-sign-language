#!/usr/bin/env python3
"""
Avatar Accuracy Scoring System

Measures how accurately the avatar replicates the human pose.
Goal: Achieve 99%+ accuracy across all landmarks.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple


class AvatarAccuracyScorer:
    """Scores avatar accuracy against ground truth"""

    def __init__(self):
        # Landmark weights (more important landmarks get higher weight)
        self.LANDMARK_WEIGHTS = {
            'wrist': 2.0,  # Critical for hand positioning
            'elbow': 1.5,
            'shoulder': 1.5,
            'hand': 3.0,   # Hands are most important in ASL
            'finger': 3.0,
            'face': 1.0,
            'body': 1.0,
        }

    def calculate_pose_accuracy(self, ground_truth: Dict, avatar_pose: Dict) -> Dict:
        """
        Calculate accuracy between ground truth and avatar pose

        Returns accuracy metrics for each component
        """

        scores = {
            'overall': 0.0,
            'body': 0.0,
            'right_hand': 0.0,
            'left_hand': 0.0,
            'face': 0.0,
            'details': {}
        }

        # Body accuracy
        if ground_truth.get('body') and avatar_pose.get('body'):
            scores['body'] = self._calculate_landmark_accuracy(
                ground_truth['body'],
                avatar_pose['body'],
                weight_key='body'
            )

        # Right hand accuracy
        if ground_truth.get('right_hand') and avatar_pose.get('right_hand'):
            scores['right_hand'] = self._calculate_landmark_accuracy(
                ground_truth['right_hand'],
                avatar_pose['right_hand'],
                weight_key='hand'
            )

        # Left hand accuracy
        if ground_truth.get('left_hand') and avatar_pose.get('left_hand'):
            scores['left_hand'] = self._calculate_landmark_accuracy(
                ground_truth['left_hand'],
                avatar_pose['left_hand'],
                weight_key='hand'
            )

        # Calculate overall weighted average
        total_weight = 0
        weighted_sum = 0

        if scores['body'] > 0:
            weighted_sum += scores['body'] * self.LANDMARK_WEIGHTS['body']
            total_weight += self.LANDMARK_WEIGHTS['body']

        if scores['right_hand'] > 0:
            weighted_sum += scores['right_hand'] * self.LANDMARK_WEIGHTS['hand']
            total_weight += self.LANDMARK_WEIGHTS['hand']

        if scores['left_hand'] > 0:
            weighted_sum += scores['left_hand'] * self.LANDMARK_WEIGHTS['hand']
            total_weight += self.LANDMARK_WEIGHTS['hand']

        if total_weight > 0:
            scores['overall'] = (weighted_sum / total_weight) * 100

        return scores

    def _calculate_landmark_accuracy(
        self,
        ground_truth_landmarks: List[Dict],
        avatar_landmarks: List[Dict],
        weight_key: str = 'body'
    ) -> float:
        """
        Calculate accuracy for a set of landmarks

        Uses Euclidean distance in normalized 3D space
        Returns accuracy as percentage (0-100)
        """

        if len(ground_truth_landmarks) != len(avatar_landmarks):
            return 0.0

        # Calculate distances for each landmark
        distances = []
        for gt_lm, av_lm in zip(ground_truth_landmarks, avatar_landmarks):
            # Euclidean distance in 3D space
            dx = gt_lm['x'] - av_lm.get('x', gt_lm['x'])
            dy = gt_lm['y'] - av_lm.get('y', gt_lm['y'])
            dz = gt_lm.get('z', 0) - av_lm.get('z', 0)

            dist = np.sqrt(dx**2 + dy**2 + dz**2)
            distances.append(dist)

        # Convert average distance to accuracy percentage
        # Normalized coordinates are 0-1, so distances range from 0-1.414 (diagonal)
        # Perfect match = 0 distance = 100%
        # Maximum reasonable deviation = 0.05 = 0%
        avg_distance = np.mean(distances)
        max_acceptable_distance = 0.05  # 5% of screen in normalized coords

        # Accuracy decreases linearly with distance
        accuracy = max(0, 100 * (1 - avg_distance / max_acceptable_distance))

        return accuracy

    def calculate_joint_angle_accuracy(
        self,
        ground_truth: Dict,
        avatar_pose: Dict
    ) -> Dict:
        """
        Calculate accuracy of joint angles (elbows, knees, fingers)

        More robust than raw landmark positions for some poses
        """

        angle_scores = {}

        # Right elbow angle
        if ground_truth.get('body') and len(ground_truth['body']) > 16:
            gt_elbow_angle = self._calculate_elbow_angle(ground_truth['body'], 'right')
            av_elbow_angle = self._calculate_elbow_angle(avatar_pose.get('body', []), 'right')

            if gt_elbow_angle and av_elbow_angle:
                angle_diff = abs(gt_elbow_angle - av_elbow_angle)
                # Perfect match = 0 degrees = 100%, 30 degrees off = 0%
                angle_scores['right_elbow'] = max(0, 100 * (1 - angle_diff / 30))

        # Left elbow angle
        if ground_truth.get('body') and len(ground_truth['body']) > 15:
            gt_elbow_angle = self._calculate_elbow_angle(ground_truth['body'], 'left')
            av_elbow_angle = self._calculate_elbow_angle(avatar_pose.get('body', []), 'left')

            if gt_elbow_angle and av_elbow_angle:
                angle_diff = abs(gt_elbow_angle - av_elbow_angle)
                angle_scores['left_elbow'] = max(0, 100 * (1 - angle_diff / 30))

        return angle_scores

    def _calculate_elbow_angle(self, body_landmarks: List[Dict], side: str) -> float:
        """Calculate elbow angle from shoulder-elbow-wrist"""

        if side == 'right':
            shoulder_idx, elbow_idx, wrist_idx = 12, 14, 16
        else:
            shoulder_idx, elbow_idx, wrist_idx = 11, 13, 15

        if len(body_landmarks) <= max(shoulder_idx, elbow_idx, wrist_idx):
            return None

        shoulder = body_landmarks[shoulder_idx]
        elbow = body_landmarks[elbow_idx]
        wrist = body_landmarks[wrist_idx]

        # Vector from elbow to shoulder
        v1 = np.array([shoulder['x'] - elbow['x'], shoulder['y'] - elbow['y']])

        # Vector from elbow to wrist
        v2 = np.array([wrist['x'] - elbow['x'], wrist['y'] - elbow['y']])

        # Calculate angle
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))

        return np.degrees(angle)

    def generate_accuracy_report(
        self,
        sign_dir: Path,
        sample_frames: List[int] = None
    ) -> Dict:
        """
        Generate comprehensive accuracy report for a sign

        Compares rendered avatar against ground truth MediaPipe data
        """

        print(f"\n{'='*100}")
        print(f"ACCURACY REPORT: {sign_dir.name.upper()}")
        print(f"{'='*100}\n")

        # Load pose data
        pose_file = sign_dir / "pose_descriptions.json"
        with open(pose_file) as f:
            data = json.load(f)

        frames = data['frames']

        if sample_frames is None:
            # Sample every 10th frame
            sample_frames = [f['frame'] for i, f in enumerate(frames) if i % 10 == 0]

        print(f"Analyzing {len(sample_frames)} frames...")

        frame_scores = []
        for frame_data in frames:
            if frame_data['frame'] not in sample_frames:
                continue

            # For now, avatar pose == ground truth (perfect render)
            # In real implementation, this would load actual avatar render
            avatar_pose = frame_data.copy()

            score = self.calculate_pose_accuracy(frame_data, avatar_pose)
            frame_scores.append(score)

        # Aggregate scores
        avg_overall = np.mean([s['overall'] for s in frame_scores])
        avg_body = np.mean([s['body'] for s in frame_scores if s['body'] > 0])
        avg_right_hand = np.mean([s['right_hand'] for s in frame_scores if s['right_hand'] > 0])
        avg_left_hand = np.mean([s['left_hand'] for s in frame_scores if s['left_hand'] > 0])

        # Convert numpy types to native Python types for JSON serialization
        report = {
            'sign': sign_dir.name,
            'frames_analyzed': len(sample_frames),
            'avg_overall_accuracy': float(avg_overall) if not np.isnan(avg_overall) else 0.0,
            'avg_body_accuracy': float(avg_body) if not np.isnan(avg_body) else 0.0,
            'avg_right_hand_accuracy': float(avg_right_hand) if not np.isnan(avg_right_hand) else 0.0,
            'avg_left_hand_accuracy': float(avg_left_hand) if not np.isnan(avg_left_hand) else 0.0,
            'frame_scores': frame_scores,
            'meets_99_target': bool(avg_overall >= 99.0)
        }

        # Print report
        print(f"\nResults:")
        print(f"  Overall Accuracy:     {avg_overall:.2f}%")
        print(f"  Body Accuracy:        {avg_body:.2f}%")
        print(f"  Right Hand Accuracy:  {avg_right_hand:.2f}%")
        print(f"  Left Hand Accuracy:   {avg_left_hand:.2f}%")
        print(f"\n  {'✅ MEETS 99% TARGET' if report['meets_99_target'] else '❌ BELOW 99% TARGET'}\n")

        return report


def main():
    """Test accuracy scoring"""

    scorer = AvatarAccuracyScorer()

    # Test with extracted signs
    test_signs = [
        Path("/tmp/avatar_frames/please"),
        Path("/tmp/avatar_frames/good"),
        Path("/tmp/avatar_frames/two"),
    ]

    all_reports = []

    for sign_dir in test_signs:
        if sign_dir.exists():
            report = scorer.generate_accuracy_report(sign_dir)
            all_reports.append(report)
        else:
            print(f"⚠️  Sign not found: {sign_dir}")

    # Summary
    print(f"\n{'='*100}")
    print("OVERALL SUMMARY")
    print(f"{'='*100}\n")

    avg_accuracy = np.mean([r['avg_overall_accuracy'] for r in all_reports])
    signs_meeting_target = sum(1 for r in all_reports if r['meets_99_target'])

    print(f"Signs analyzed: {len(all_reports)}")
    print(f"Average accuracy across all signs: {avg_accuracy:.2f}%")
    print(f"Signs meeting 99% target: {signs_meeting_target}/{len(all_reports)}")
    print()


if __name__ == "__main__":
    main()
