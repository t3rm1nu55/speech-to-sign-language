"""
Sign Validation Service
Validates MediaPipe pose interpretations against ASL linguistic descriptions
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import math
from app.models.sign_description import (
    SignDescription, SignValidationResult, ValidationReport,
    Handshape, Location, Movement, PalmOrientation, NonManualMarker
)
from app.services.pose_extraction import PoseExtractionService
import logging

logger = logging.getLogger(__name__)


class SignValidationService:
    """
    Validates sign interpretations using ASL linguistic framework
    """

    def __init__(self):
        self.pose_service = PoseExtractionService()

        # MediaPipe landmark indices for key features
        self.LANDMARK_INDICES = {
            'left_wrist': 15,
            'right_wrist': 16,
            'left_thumb': 21,
            'right_thumb': 22,
            'left_index': 19,
            'right_index': 20,
            'left_pinky': 17,
            'right_pinky': 18,
            'nose': 0,
            'left_shoulder': 11,
            'right_shoulder': 12,
            'left_eye': 2,
            'right_eye': 5,
            'mouth': 10,
        }

        # Location zones in normalized coordinates
        self.LOCATION_ZONES = {
            Location.FOREHEAD: {'y_min': 0.0, 'y_max': 0.2, 'x_center': 0.5},
            Location.EYE: {'y_min': 0.15, 'y_max': 0.25, 'x_center': 0.5},
            Location.NOSE: {'y_min': 0.25, 'y_max': 0.35, 'x_center': 0.5},
            Location.MOUTH: {'y_min': 0.35, 'y_max': 0.45, 'x_center': 0.5},
            Location.CHIN: {'y_min': 0.45, 'y_max': 0.55, 'x_center': 0.5},
            Location.NECK: {'y_min': 0.55, 'y_max': 0.65, 'x_center': 0.5},
            Location.CHEST: {'y_min': 0.65, 'y_max': 0.85, 'x_center': 0.5},
            Location.NEUTRAL_SPACE: {'y_min': 0.5, 'y_max': 0.9, 'x_range': (0.3, 0.7)},
            Location.HIGH_SPACE: {'y_min': 0.0, 'y_max': 0.5},
            Location.LOW_SPACE: {'y_min': 0.85, 'y_max': 1.0},
        }

    def validate_sign(
        self,
        video_url: str,
        expected_description: SignDescription,
        max_frames: int = 30
    ) -> SignValidationResult:
        """
        Validate a sign interpretation against expected linguistic description

        Args:
            video_url: URL of sign video
            expected_description: Expected sign features
            max_frames: Maximum frames to analyze

        Returns:
            Validation result with diagnostics
        """
        result = SignValidationResult(
            gloss=expected_description.gloss,
            video_url=video_url,
            passed=False,
            confidence_score=0.0,
            expected_description=expected_description
        )

        try:
            # Extract pose data from video
            logger.info(f"Extracting pose from {video_url}")
            pose_data = self.pose_service.extract_pose_from_video(
                video_url,
                max_frames=max_frames
            )

            if not pose_data.get('success', False):
                result.issues_found.append("Failed to extract pose from video")
                result.diagnostics['pose_extraction'] = 'failed'
                return result

            frames = pose_data.get('frames', [])
            if not frames:
                result.issues_found.append("No frames extracted from video")
                return result

            result.frame_count = len(frames)

            # Calculate pose detection rate
            frames_with_pose = sum(
                1 for f in frames
                if f.get('pose') and len(f['pose']) >= 33
            )
            result.pose_detection_rate = frames_with_pose / len(frames) if frames else 0

            # Video quality check
            result.video_quality_score = self._assess_video_quality(frames)
            if result.video_quality_score < 0.5:
                result.issues_found.append(
                    f"Poor video quality (score: {result.video_quality_score:.2f})"
                )

            # Extract features from pose data
            extracted = self._extract_sign_features(frames)
            result.extracted_features = extracted

            # Validate each parameter
            scores = []

            # 1. Handshape validation
            if expected_description.dominant_hand.handshape != Handshape.UNKNOWN:
                handshape_valid, handshape_conf = self._validate_handshape(
                    extracted,
                    expected_description.dominant_hand.handshape,
                    frames
                )
                result.handshape_match = handshape_valid
                result.handshape_confidence = handshape_conf
                scores.append(handshape_conf)

                if not handshape_valid:
                    result.issues_found.append(
                        f"Handshape mismatch: expected {expected_description.dominant_hand.handshape}, "
                        f"detected {extracted.get('handshape', 'unknown')}"
                    )

            # 2. Location validation
            if expected_description.dominant_hand.location != Location.UNKNOWN:
                location_valid, location_conf = self._validate_location(
                    extracted,
                    expected_description.dominant_hand.location
                )
                result.location_match = location_valid
                result.location_confidence = location_conf
                scores.append(location_conf)

                if not location_valid:
                    result.issues_found.append(
                        f"Location mismatch: expected {expected_description.dominant_hand.location}, "
                        f"detected {extracted.get('location', 'unknown')}"
                    )

            # 3. Movement validation
            if expected_description.movement != Movement.UNKNOWN:
                movement_valid, movement_conf = self._validate_movement(
                    extracted,
                    expected_description.movement
                )
                result.movement_match = movement_valid
                result.movement_confidence = movement_conf
                scores.append(movement_conf)

                if not movement_valid:
                    result.issues_found.append(
                        f"Movement mismatch: expected {expected_description.movement}, "
                        f"detected {extracted.get('movement', 'unknown')}"
                    )

            # 4. Palm orientation validation
            if expected_description.dominant_hand.palm_orientation != PalmOrientation.UNKNOWN:
                palm_valid, palm_conf = self._validate_palm_orientation(
                    extracted,
                    expected_description.dominant_hand.palm_orientation
                )
                result.palm_orientation_match = palm_valid
                result.palm_orientation_confidence = palm_conf
                scores.append(palm_conf)

                if not palm_valid:
                    result.issues_found.append(
                        f"Palm orientation mismatch: expected "
                        f"{expected_description.dominant_hand.palm_orientation}"
                    )

            # Calculate overall confidence
            if scores:
                result.confidence_score = np.mean(scores)

            # Determine if passed (threshold: 0.7)
            result.passed = result.confidence_score >= 0.7 and len(result.issues_found) == 0

            # Generate suggestions
            result.suggestions = self._generate_suggestions(result, extracted)

            return result

        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            result.issues_found.append(f"Validation error: {str(e)}")
            result.diagnostics['error'] = str(e)
            return result

    def _filter_active_signing_frames(self, frames: List[Dict]) -> List[Dict]:
        """
        Filter frames to focus on active signing (hands visible and moving)

        Based on visual analysis:
        - Wrist visibility < 0.60: Hands at rest, not detected
        - Wrist visibility > 0.65: Hands actively signing, reliably detected

        Args:
            frames: All frames from video

        Returns:
            Frames where hands are actively signing
        """
        active_frames = []

        for frame in frames:
            pose = frame.get('pose')
            if not pose or len(pose) < 17:
                continue

            # Check wrist visibility (landmarks 15=left wrist, 16=right wrist)
            left_wrist_vis = pose[15].get('visibility', 0) if len(pose) > 15 else 0
            right_wrist_vis = pose[16].get('visibility', 0) if len(pose) > 16 else 0

            # Include frame if either wrist has high visibility (>0.65)
            if left_wrist_vis > 0.65 or right_wrist_vis > 0.65:
                active_frames.append(frame)

        # If we filtered out too many frames, return all frames
        # (better to have some data than none)
        if len(active_frames) < 3 and len(frames) > 0:
            logger.warning(f"Only {len(active_frames)} active frames found, using all {len(frames)} frames")
            return frames

        logger.info(f"Filtered {len(frames)} frames to {len(active_frames)} active signing frames")
        return active_frames

    def _assess_video_quality(self, frames: List[Dict]) -> float:
        """
        Assess video quality based on pose detection consistency

        Args:
            frames: List of frame data

        Returns:
            Quality score (0-1)
        """
        if not frames:
            return 0.0

        quality_factors = []

        # 1. Pose detection rate
        poses_detected = sum(
            1 for f in frames
            if f.get('pose') and len(f['pose']) >= 33
        )
        detection_rate = poses_detected / len(frames)
        quality_factors.append(detection_rate)

        # 2. Hand detection rate (null-safe)
        hands_detected = sum(
            1 for f in frames
            if (f.get('left_hand') is not None and len(f['left_hand']) >= 21) or
               (f.get('right_hand') is not None and len(f['right_hand']) >= 21)
        )
        hand_rate = hands_detected / len(frames) if len(frames) > 0 else 0.0
        quality_factors.append(hand_rate)

        # 3. Landmark visibility (average)
        visible_landmarks = []
        for frame in frames:
            pose = frame.get('pose')
            if pose:
                visibilities = [
                    p.get('visibility', 0) for p in pose
                    if isinstance(p, dict)
                ]
                if visibilities:
                    visible_landmarks.append(np.mean(visibilities))

        if visible_landmarks:
            quality_factors.append(np.mean(visible_landmarks))

        return np.mean(quality_factors) if quality_factors else 0.0

    def _extract_sign_features(self, frames: List[Dict]) -> Dict:
        """
        Extract sign features from pose data

        Args:
            frames: List of frame data with pose landmarks

        Returns:
            Dictionary of extracted features
        """
        features = {
            'handshape': Handshape.UNKNOWN,
            'location': Location.UNKNOWN,
            'movement': Movement.UNKNOWN,
            'palm_orientation': PalmOrientation.UNKNOWN,
            'hand_positions': [],
            'movement_vector': None,
            'hand_velocity': None,
        }

        # Filter to active signing frames (wrist visibility > 0.65)
        active_frames = self._filter_active_signing_frames(frames)

        valid_frames = [f for f in active_frames if f.get('pose') and len(f['pose']) >= 33]
        if not valid_frames:
            logger.warning("No valid frames with pose data after filtering")
            return features

        # Extract hand positions across frames
        for frame in valid_frames:
            pose = frame['pose']
            if len(pose) > 16:  # Ensure we have hand landmarks
                # Right hand position (dominant for most signers)
                right_wrist = pose[16]
                features['hand_positions'].append({
                    'x': right_wrist['x'],
                    'y': right_wrist['y'],
                    'z': right_wrist['z']
                })

        # Analyze handshape from hand landmarks (use active frames)
        features['handshape'] = self._detect_handshape(active_frames)

        # Analyze location (where in signing space)
        features['location'] = self._detect_location(features['hand_positions'])

        # Analyze movement
        features['movement'] = self._detect_movement(features['hand_positions'])

        # Calculate movement vector and velocity
        if len(features['hand_positions']) >= 2:
            start_pos = features['hand_positions'][0]
            end_pos = features['hand_positions'][-1]
            features['movement_vector'] = {
                'x': end_pos['x'] - start_pos['x'],
                'y': end_pos['y'] - start_pos['y'],
                'z': end_pos['z'] - start_pos['z']
            }

            # Calculate average velocity
            distances = []
            for i in range(1, len(features['hand_positions'])):
                prev = features['hand_positions'][i-1]
                curr = features['hand_positions'][i]
                dist = math.sqrt(
                    (curr['x'] - prev['x'])**2 +
                    (curr['y'] - prev['y'])**2 +
                    (curr['z'] - prev['z'])**2
                )
                distances.append(dist)

            features['hand_velocity'] = np.mean(distances) if distances else 0.0

        # Analyze palm orientation (use active frames)
        features['palm_orientation'] = self._detect_palm_orientation(active_frames)

        return features

    def _detect_handshape(self, frames: List[Dict]) -> Handshape:
        """
        Detect handshape from hand landmarks

        This is a simplified heuristic - real handshape recognition requires ML
        """
        # Look for frames with hand data
        for frame in frames:
            right_hand = frame.get('right_hand')
            # Null-safe check: right_hand could be None or missing
            if right_hand is not None and len(right_hand) >= 21:
                return self._classify_handshape(right_hand)

            # Try left hand if right hand not available
            left_hand = frame.get('left_hand')
            if left_hand is not None and len(left_hand) >= 21:
                return self._classify_handshape(left_hand)

        return Handshape.UNKNOWN

    def _classify_handshape(self, hand_landmarks: List[Dict]) -> Handshape:
        """
        Classify handshape based on finger positions

        Simplified heuristic analysis
        """
        if len(hand_landmarks) < 21:
            return Handshape.UNKNOWN

        # Calculate which fingers are extended
        wrist = hand_landmarks[0]

        # Check each finger tip vs base
        fingers_extended = []

        # Thumb (1-4)
        thumb_tip = hand_landmarks[4]
        thumb_base = hand_landmarks[2]
        thumb_dist = self._distance_3d(thumb_tip, wrist)
        thumb_base_dist = self._distance_3d(thumb_base, wrist)
        fingers_extended.append(thumb_dist > thumb_base_dist * 1.2)

        # Index (5-8)
        index_tip = hand_landmarks[8]
        index_base = hand_landmarks[5]
        index_dist = self._distance_3d(index_tip, wrist)
        index_base_dist = self._distance_3d(index_base, wrist)
        fingers_extended.append(index_dist > index_base_dist * 1.3)

        # Middle (9-12)
        middle_tip = hand_landmarks[12]
        middle_base = hand_landmarks[9]
        middle_dist = self._distance_3d(middle_tip, wrist)
        middle_base_dist = self._distance_3d(middle_base, wrist)
        fingers_extended.append(middle_dist > middle_base_dist * 1.3)

        # Ring (13-16)
        ring_tip = hand_landmarks[16]
        ring_base = hand_landmarks[13]
        ring_dist = self._distance_3d(ring_tip, wrist)
        ring_base_dist = self._distance_3d(ring_base, wrist)
        fingers_extended.append(ring_dist > ring_base_dist * 1.3)

        # Pinky (17-20)
        pinky_tip = hand_landmarks[20]
        pinky_base = hand_landmarks[17]
        pinky_dist = self._distance_3d(pinky_tip, wrist)
        pinky_base_dist = self._distance_3d(pinky_base, wrist)
        fingers_extended.append(pinky_dist > pinky_base_dist * 1.3)

        # Classify based on extended fingers
        num_extended = sum(fingers_extended)

        if num_extended == 5:
            return Handshape.FIVE
        elif num_extended == 4 and not fingers_extended[0]:  # Thumb not extended
            return Handshape.FOUR
        elif num_extended == 1 and fingers_extended[1]:  # Only index
            return Handshape.ONE
        elif num_extended == 2 and fingers_extended[1] and fingers_extended[2]:
            return Handshape.TWO
        elif num_extended == 0:
            return Handshape.FIST
        else:
            # Check for special shapes
            if fingers_extended[1] and fingers_extended[4]:  # Index and pinky
                return Handshape.HORNS

        return Handshape.UNKNOWN

    def _detect_location(self, hand_positions: List[Dict]) -> Location:
        """
        Detect location in signing space based on hand position
        """
        if not hand_positions:
            return Location.UNKNOWN

        # Use average position
        avg_y = np.mean([p['y'] for p in hand_positions])
        avg_x = np.mean([p['x'] for p in hand_positions])

        # Check against location zones
        for location, zone in self.LOCATION_ZONES.items():
            if 'y_min' in zone and 'y_max' in zone:
                if zone['y_min'] <= avg_y <= zone['y_max']:
                    # Check x range if specified
                    if 'x_range' in zone:
                        if zone['x_range'][0] <= avg_x <= zone['x_range'][1]:
                            return location
                    elif 'x_center' in zone:
                        # Check if near center
                        if abs(avg_x - zone['x_center']) < 0.3:
                            return location

        return Location.NEUTRAL_SPACE

    def _detect_movement(self, hand_positions: List[Dict]) -> Movement:
        """
        Detect movement type from hand trajectory
        """
        if len(hand_positions) < 3:
            return Movement.NONE

        # Calculate movement vector
        start = hand_positions[0]
        end = hand_positions[-1]

        dx = end['x'] - start['x']
        dy = end['y'] - start['y']
        dz = end['z'] - start['z']

        # Total distance
        total_dist = math.sqrt(dx**2 + dy**2 + dz**2)

        # If minimal movement, it's static
        if total_dist < 0.05:
            return Movement.NONE

        # Determine primary direction
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        abs_dz = abs(dz)

        max_component = max(abs_dx, abs_dy, abs_dz)

        if max_component == abs_dy:
            return Movement.UP if dy < 0 else Movement.DOWN
        elif max_component == abs_dx:
            return Movement.RIGHT if dx > 0 else Movement.LEFT
        elif max_component == abs_dz:
            return Movement.FORWARD if dz > 0 else Movement.BACKWARD

        # Check for circular motion
        if self._is_circular_motion(hand_positions):
            return Movement.CIRCLE

        return Movement.UNKNOWN

    def _is_circular_motion(self, positions: List[Dict]) -> bool:
        """
        Detect if motion is circular
        """
        if len(positions) < 10:
            return False

        # Calculate center point
        center_x = np.mean([p['x'] for p in positions])
        center_y = np.mean([p['y'] for p in positions])

        # Calculate distances from center
        distances = [
            math.sqrt((p['x'] - center_x)**2 + (p['y'] - center_y)**2)
            for p in positions
        ]

        # Check if distances are relatively constant (circular)
        std_dev = np.std(distances)
        mean_dist = np.mean(distances)

        # If standard deviation is small relative to mean, it's circular
        return (std_dev / mean_dist) < 0.3 if mean_dist > 0 else False

    def _detect_palm_orientation(self, frames: List[Dict]) -> PalmOrientation:
        """
        Detect palm orientation from hand landmarks
        """
        # Simplified - would need hand normal vector calculation
        return PalmOrientation.UNKNOWN

    def _distance_3d(self, p1: Dict, p2: Dict) -> float:
        """Calculate 3D Euclidean distance"""
        return math.sqrt(
            (p1['x'] - p2['x'])**2 +
            (p1['y'] - p2['y'])**2 +
            (p1['z'] - p2['z'])**2
        )

    def _validate_handshape(
        self,
        extracted: Dict,
        expected: Handshape,
        frames: List[Dict]
    ) -> Tuple[bool, float]:
        """Validate handshape match"""
        detected = extracted.get('handshape', Handshape.UNKNOWN)

        if detected == Handshape.UNKNOWN:
            return False, 0.3  # Low confidence if can't detect

        if detected == expected:
            return True, 0.95

        # Partial matches (similar shapes)
        similar_groups = [
            {Handshape.ONE, Handshape.INDEX},
            {Handshape.FIVE, Handshape.FLAT},
            {Handshape.FIST, Handshape.A},
        ]

        for group in similar_groups:
            if detected in group and expected in group:
                return True, 0.7  # Partial match

        return False, 0.2

    def _validate_location(
        self,
        extracted: Dict,
        expected: Location
    ) -> Tuple[bool, float]:
        """Validate location match"""
        detected = extracted.get('location', Location.UNKNOWN)

        if detected == expected:
            return True, 0.9

        # Adjacent locations are partial matches
        adjacent = {
            Location.FOREHEAD: {Location.TEMPLE, Location.EYE},
            Location.NOSE: {Location.EYE, Location.MOUTH},
            Location.CHIN: {Location.MOUTH, Location.NECK},
        }

        if expected in adjacent and detected in adjacent[expected]:
            return True, 0.6

        return False, 0.3

    def _validate_movement(
        self,
        extracted: Dict,
        expected: Movement
    ) -> Tuple[bool, float]:
        """Validate movement match"""
        detected = extracted.get('movement', Movement.UNKNOWN)

        if detected == expected:
            return True, 0.85

        # Opposite directions are clear mismatches
        opposites = {
            (Movement.UP, Movement.DOWN),
            (Movement.LEFT, Movement.RIGHT),
            (Movement.FORWARD, Movement.BACKWARD),
        }

        for opp1, opp2 in opposites:
            if (detected == opp1 and expected == opp2) or \
               (detected == opp2 and expected == opp1):
                return False, 0.1

        return False, 0.4

    def _validate_palm_orientation(
        self,
        extracted: Dict,
        expected: PalmOrientation
    ) -> Tuple[bool, float]:
        """Validate palm orientation"""
        # Simplified for now
        return True, 0.5  # Neutral confidence

    def _generate_suggestions(
        self,
        result: SignValidationResult,
        extracted: Dict
    ) -> List[str]:
        """Generate improvement suggestions based on validation results"""
        suggestions = []

        if result.video_quality_score and result.video_quality_score < 0.7:
            suggestions.append(
                "Consider using a higher quality video with better pose detection"
            )

        if result.pose_detection_rate and result.pose_detection_rate < 0.8:
            suggestions.append(
                "Pose detection is inconsistent - ensure good lighting and clear view of signer"
            )

        if result.handshape_confidence and result.handshape_confidence < 0.6:
            suggestions.append(
                "Handshape detection is uncertain - may need closer view of hands or "
                "improved hand tracking"
            )

        if result.movement_confidence and result.movement_confidence < 0.6:
            suggestions.append(
                "Movement detection is ambiguous - ensure video captures full sign motion"
            )

        if extracted.get('hand_velocity', 0) < 0.01:
            suggestions.append(
                "Very little movement detected - check if sign is truly static or "
                "if video quality is limiting motion detection"
            )

        return suggestions
