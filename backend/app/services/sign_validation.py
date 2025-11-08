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

        # Analyze location (where in signing space) - pass frames for pose context
        features['location'] = self._detect_location(features['hand_positions'], valid_frames)

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

        Improved algorithm with better finger extension detection
        and more handshape patterns
        """
        if len(hand_landmarks) < 21:
            return Handshape.UNKNOWN

        # Calculate which fingers are extended using improved heuristics
        wrist = hand_landmarks[0]

        # For each finger, check both extension and curl
        fingers_extended = []
        finger_curls = []

        # Thumb (1-4): landmarks are tip=4, ip=3, mcp=2, cmc=1
        thumb_tip = hand_landmarks[4]
        thumb_ip = hand_landmarks[3]
        thumb_mcp = hand_landmarks[2]

        # Thumb extension: tip distance from wrist vs mcp distance
        thumb_tip_dist = self._distance_3d(thumb_tip, wrist)
        thumb_mcp_dist = self._distance_3d(thumb_mcp, wrist)
        thumb_extended = thumb_tip_dist > thumb_mcp_dist * 1.4  # Stricter threshold
        fingers_extended.append(thumb_extended)

        # Thumb curl: tip distance from mcp vs ip distance from mcp
        thumb_curl = self._distance_3d(thumb_tip, thumb_mcp) / max(self._distance_3d(thumb_ip, thumb_mcp), 0.01)
        finger_curls.append(thumb_curl)

        # Index finger (5-8): landmarks are tip=8, dip=7, pip=6, mcp=5
        index_tip = hand_landmarks[8]
        index_dip = hand_landmarks[7]
        index_pip = hand_landmarks[6]
        index_mcp = hand_landmarks[5]

        index_extended = self._is_finger_extended(index_tip, index_pip, index_mcp, wrist)
        fingers_extended.append(index_extended)
        index_curl = self._calculate_finger_curl(index_tip, index_dip, index_pip, index_mcp)
        finger_curls.append(index_curl)

        # Middle finger (9-12)
        middle_tip = hand_landmarks[12]
        middle_dip = hand_landmarks[11]
        middle_pip = hand_landmarks[10]
        middle_mcp = hand_landmarks[9]

        middle_extended = self._is_finger_extended(middle_tip, middle_pip, middle_mcp, wrist)
        fingers_extended.append(middle_extended)
        middle_curl = self._calculate_finger_curl(middle_tip, middle_dip, middle_pip, middle_mcp)
        finger_curls.append(middle_curl)

        # Ring finger (13-16)
        ring_tip = hand_landmarks[16]
        ring_dip = hand_landmarks[15]
        ring_pip = hand_landmarks[14]
        ring_mcp = hand_landmarks[13]

        ring_extended = self._is_finger_extended(ring_tip, ring_pip, ring_mcp, wrist)
        fingers_extended.append(ring_extended)
        ring_curl = self._calculate_finger_curl(ring_tip, ring_dip, ring_pip, ring_mcp)
        finger_curls.append(ring_curl)

        # Pinky finger (17-20)
        pinky_tip = hand_landmarks[20]
        pinky_dip = hand_landmarks[19]
        pinky_pip = hand_landmarks[18]
        pinky_mcp = hand_landmarks[17]

        pinky_extended = self._is_finger_extended(pinky_tip, pinky_pip, pinky_mcp, wrist)
        fingers_extended.append(pinky_extended)
        pinky_curl = self._calculate_finger_curl(pinky_tip, pinky_dip, pinky_pip, pinky_mcp)
        finger_curls.append(pinky_curl)

        # Count extended fingers
        num_extended = sum(fingers_extended)

        # Average curl of four fingers (excluding thumb)
        avg_finger_curl = np.mean(finger_curls[1:]) if len(finger_curls) > 1 else 1.0

        # Classify based on finger patterns
        # Number handshapes (most common)
        if num_extended == 0:
            # All fingers curled - could be FIST or A
            # A has thumb to the side, FIST has thumb wrapped
            if thumb_curl < 1.5:  # Thumb relatively extended to side
                return Handshape.A
            return Handshape.FIST

        elif num_extended == 1:
            if fingers_extended[1]:  # Only index
                return Handshape.ONE
            elif fingers_extended[0]:  # Only thumb
                # Thumb up gesture - but we don't have this enum, default to UNKNOWN
                return Handshape.UNKNOWN

        elif num_extended == 2:
            if fingers_extended[1] and fingers_extended[2]:  # Index + middle
                # Could be TWO or V
                # Check if fingers are spread apart
                spread = self._distance_3d(index_tip, middle_tip)
                if spread > 0.08:  # Fingers spread apart
                    return Handshape.V
                return Handshape.TWO
            elif fingers_extended[1] and fingers_extended[4]:  # Index + pinky
                return Handshape.HORNS
            elif fingers_extended[0] and fingers_extended[1]:  # Thumb + index
                # Could be L or gun shape
                return Handshape.L

        elif num_extended == 3:
            if fingers_extended[1] and fingers_extended[2] and fingers_extended[3]:
                # Index, middle, ring = THREE
                return Handshape.THREE
            elif fingers_extended[0] and fingers_extended[1] and fingers_extended[4]:
                # Thumb, index, pinky = I_LOVE_YOU
                return Handshape.I_LOVE_YOU

        elif num_extended == 4:
            if not fingers_extended[0]:  # Four fingers, no thumb
                return Handshape.FOUR
            elif not fingers_extended[4]:  # Thumb + 3 fingers, no pinky
                return Handshape.UNKNOWN

        elif num_extended == 5:
            # All fingers extended - could be FIVE or B (flat)
            # Check if fingers are together (B) or spread (FIVE)
            finger_spread = (
                self._distance_3d(index_tip, middle_tip) +
                self._distance_3d(middle_tip, ring_tip) +
                self._distance_3d(ring_tip, pinky_tip)
            ) / 3

            if finger_spread < 0.04:  # Fingers together
                return Handshape.B
            return Handshape.FIVE

        # Check for special shapes based on curl patterns
        # C shape: all fingers partially curled in same direction
        if 1.2 < avg_finger_curl < 2.0 and max(finger_curls[1:]) - min(finger_curls[1:]) < 0.5:
            return Handshape.C

        # O shape: fingers touching thumb (very curled, small circle)
        if avg_finger_curl < 1.3 and num_extended <= 1:
            # Check if index tip is close to thumb tip
            if self._distance_3d(index_tip, thumb_tip) < 0.05:
                return Handshape.O

        # Flat hand: all fingers extended and together, thumb may be extended or tucked
        if num_extended >= 4 and avg_finger_curl > 2.0:
            return Handshape.FLAT

        return Handshape.UNKNOWN

    def _is_finger_extended(self, tip: Dict, pip: Dict, mcp: Dict, wrist: Dict) -> bool:
        """
        Determine if a finger is extended using improved heuristics

        Args:
            tip: Fingertip landmark
            pip: Proximal interphalangeal joint (middle joint)
            mcp: Metacarpophalangeal joint (base joint)
            wrist: Wrist landmark

        Returns:
            True if finger is extended, False if curled
        """
        # Method 1: Compare tip-to-wrist distance vs mcp-to-wrist distance
        tip_dist = self._distance_3d(tip, wrist)
        mcp_dist = self._distance_3d(mcp, wrist)

        # Balanced threshold: tip must be 1.3x farther than mcp
        extension_ratio = tip_dist / max(mcp_dist, 0.01)

        # Method 2: Check if tip is farther from wrist than pip
        pip_dist = self._distance_3d(pip, wrist)
        progressive = tip_dist > pip_dist * 0.95  # Allow small tolerance

        # Finger is extended if either condition is strongly met
        # OR both are moderately met
        strong_extension = extension_ratio > 1.4
        moderate_extension = extension_ratio > 1.25 and progressive

        return strong_extension or moderate_extension

    def _calculate_finger_curl(self, tip: Dict, dip: Dict, pip: Dict, mcp: Dict) -> float:
        """
        Calculate finger curl factor

        Args:
            tip: Fingertip landmark
            dip: Distal interphalangeal joint
            pip: Proximal interphalangeal joint
            mcp: Metacarpophalangeal joint (base)

        Returns:
            Curl factor: higher = more extended, lower = more curled
            Typical range: 0.5 (very curled) to 3.0 (fully extended)
        """
        # Calculate distances between joints
        tip_to_mcp = self._distance_3d(tip, mcp)
        dip_to_mcp = self._distance_3d(dip, mcp)
        pip_to_mcp = self._distance_3d(pip, mcp)

        # Full extension: tip is far from base
        # Full curl: tip is close to base
        # Normalize by pip distance to account for finger length
        curl_factor = tip_to_mcp / max(pip_to_mcp, 0.01)

        return curl_factor

    def _detect_location(self, hand_positions: List[Dict], frames: List[Dict] = None) -> Location:
        """
        Detect location in signing space based on hand position relative to body

        Uses facial landmarks and shoulders to determine precise location zones
        """
        if not hand_positions:
            return Location.UNKNOWN

        # Use average hand position
        avg_hand_y = np.mean([p['y'] for p in hand_positions])
        avg_hand_x = np.mean([p['x'] for p in hand_positions])

        # If frames available, use pose landmarks for relative positioning
        if frames and len(frames) > 0:
            # Extract key pose landmarks from first valid frame
            for frame in frames:
                pose = frame.get('pose')
                if pose and len(pose) >= 33:
                    # Get facial landmarks (MediaPipe indices)
                    # 0=nose, 2=left_eye, 5=right_eye, 10=mouth
                    nose = pose[0] if len(pose) > 0 else None
                    left_eye = pose[2] if len(pose) > 2 else None
                    right_eye = pose[5] if len(pose) > 5 else None
                    mouth = pose[10] if len(pose) > 10 else None

                    # Get shoulder landmarks
                    left_shoulder = pose[11] if len(pose) > 11 else None
                    right_shoulder = pose[12] if len(pose) > 12 else None

                    if nose and left_shoulder and right_shoulder:
                        # Calculate relative zones based on actual body landmarks
                        nose_y = nose['y']
                        eye_y = (left_eye['y'] + right_eye['y']) / 2 if left_eye and right_eye else nose_y - 0.05
                        mouth_y = mouth['y'] if mouth else nose_y + 0.05
                        shoulder_y = (left_shoulder['y'] + right_shoulder['y']) / 2

                        # Define face zones relative to landmarks
                        forehead_y = eye_y - 0.08  # Above eyes
                        chin_y = mouth_y + 0.08   # Below mouth
                        neck_y = chin_y + 0.1     # Below chin

                        # Chest area starts below shoulders
                        chest_top = shoulder_y + 0.05
                        chest_bottom = shoulder_y + 0.25

                        # Check hand position against body-relative zones
                        # Face zones (must also be near centerline)
                        face_center_x = nose['x']
                        near_center = abs(avg_hand_x - face_center_x) < 0.25

                        if near_center:
                            if avg_hand_y < eye_y:
                                # Above eyes
                                return Location.FOREHEAD
                            elif avg_hand_y < nose_y:
                                # Eye level
                                return Location.EYE
                            elif avg_hand_y < mouth_y:
                                # Nose level
                                return Location.NOSE
                            elif avg_hand_y < chin_y:
                                # Mouth level
                                return Location.MOUTH
                            elif avg_hand_y < neck_y:
                                # Chin/jaw level
                                return Location.CHIN
                            elif avg_hand_y < chest_top:
                                # Neck level
                                return Location.NECK

                        # Chest zone (wider area)
                        if chest_top <= avg_hand_y <= chest_bottom:
                            # Check if near body center
                            body_center_x = (left_shoulder['x'] + right_shoulder['x']) / 2
                            if abs(avg_hand_x - body_center_x) < 0.3:
                                return Location.CHEST

                        # Side locations (cheek, temple, ear, shoulder)
                        if eye_y <= avg_hand_y <= chin_y:
                            # Check if on left or right side of face
                            if avg_hand_x < face_center_x - 0.15:
                                # Left side of face
                                if avg_hand_y < nose_y:
                                    return Location.TEMPLE
                                else:
                                    return Location.CHEEK
                            elif avg_hand_x > face_center_x + 0.15:
                                # Right side of face
                                if avg_hand_y < nose_y:
                                    return Location.TEMPLE
                                else:
                                    return Location.CHEEK

                        # Shoulder locations
                        if abs(avg_hand_y - shoulder_y) < 0.1:
                            if abs(avg_hand_x - left_shoulder['x']) < 0.15:
                                return Location.SHOULDER
                            elif abs(avg_hand_x - right_shoulder['x']) < 0.15:
                                return Location.SHOULDER

                        # High space (above forehead)
                        if avg_hand_y < forehead_y:
                            return Location.HIGH_SPACE

                        # Low space (below chest)
                        if avg_hand_y > chest_bottom:
                            return Location.LOW_SPACE

                        # Neutral space (in front of body, not touching)
                        # Typically between shoulders and below chin
                        if neck_y < avg_hand_y < chest_bottom:
                            return Location.NEUTRAL_SPACE

                        # Default to neutral space if none of the above
                        return Location.NEUTRAL_SPACE

                    # If we reached here, we have pose data but didn't match any zone
                    # Return neutral space as reasonable default
                    return Location.NEUTRAL_SPACE

        # Fallback: use absolute normalized coordinates (if no pose data)
        # This is a rough estimate when we don't have facial landmarks
        if avg_hand_y < 0.2:
            return Location.HIGH_SPACE
        elif avg_hand_y < 0.35:
            return Location.FOREHEAD
        elif avg_hand_y < 0.45:
            return Location.EYE
        elif avg_hand_y < 0.55:
            return Location.NOSE
        elif avg_hand_y < 0.65:
            return Location.MOUTH
        elif avg_hand_y < 0.75:
            return Location.CHIN
        elif avg_hand_y < 0.85:
            return Location.CHEST
        elif avg_hand_y < 0.95:
            return Location.NEUTRAL_SPACE
        else:
            return Location.LOW_SPACE

    def _detect_movement(self, hand_positions: List[Dict]) -> Movement:
        """
        Detect movement type from hand trajectory

        Improved algorithm with better pattern recognition
        """
        if len(hand_positions) < 3:
            return Movement.NONE

        # Calculate movement vector
        start = hand_positions[0]
        end = hand_positions[-1]

        dx = end['x'] - start['x']
        dy = end['y'] - start['y']
        dz = end['z'] - start['z']

        # Total displacement
        total_dist = math.sqrt(dx**2 + dy**2 + dz**2)

        # Calculate path length (sum of all segments)
        path_length = 0.0
        for i in range(1, len(hand_positions)):
            prev = hand_positions[i-1]
            curr = hand_positions[i]
            segment = math.sqrt(
                (curr['x'] - prev['x'])**2 +
                (curr['y'] - prev['y'])**2 +
                (curr['z'] - prev['z'])**2
            )
            path_length += segment

        # If minimal movement, check if it's CONTACT or truly NONE
        if total_dist < 0.05:
            # Very little displacement - could be contact or static
            if path_length < 0.02:
                return Movement.NONE
            else:
                # Some motion but no net displacement = possibly contact/tap
                return Movement.CONTACT

        # Check for circular motion first (before directional)
        if self._is_circular_motion(hand_positions):
            return Movement.CIRCLE

        # Check for alternating/repeated motion
        if self._is_alternating_motion(hand_positions):
            return Movement.ALTERNATING

        # Determine if movement is more complex than a straight line
        # If path_length >> total_dist, it's a curved path
        path_efficiency = total_dist / max(path_length, 0.01)

        # Curved or complex movements
        if path_efficiency < 0.6:
            # Movement is not a straight line
            # Could be arc, wave, zigzag
            if self._is_arc_motion(hand_positions):
                return Movement.ARC
            return Movement.UNKNOWN

        # Straight-line directional movements
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        abs_dz = abs(dz)

        max_component = max(abs_dx, abs_dy, abs_dz)

        # Determine primary direction (with stricter thresholds)
        # Require at least 60% of movement in primary direction
        if max_component == abs_dy and abs_dy > total_dist * 0.6:
            return Movement.UP if dy < 0 else Movement.DOWN
        elif max_component == abs_dx and abs_dx > total_dist * 0.6:
            return Movement.RIGHT if dx > 0 else Movement.LEFT
        elif max_component == abs_dz and abs_dz > total_dist * 0.6:
            return Movement.FORWARD if dz > 0 else Movement.BACKWARD

        # Mixed diagonal movement - check for dominant combination
        if abs_dx > total_dist * 0.4 and abs_dy > total_dist * 0.4:
            # Diagonal movement
            return Movement.UNKNOWN  # Could add diagonal enums if needed

        return Movement.UNKNOWN

    def _is_circular_motion(self, positions: List[Dict]) -> bool:
        """
        Detect if motion is circular

        Improved with angle change detection
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
        constant_radius = (std_dev / mean_dist) < 0.3 if mean_dist > 0.02 else False

        if not constant_radius:
            return False

        # Also check for continuous angle change (should sum to ~360 degrees)
        angles = []
        for p in positions:
            angle = math.atan2(p['y'] - center_y, p['x'] - center_x)
            angles.append(angle)

        # Calculate total angle traversed
        total_angle_change = 0
        for i in range(1, len(angles)):
            delta = angles[i] - angles[i-1]
            # Normalize to -pi to pi
            if delta > math.pi:
                delta -= 2 * math.pi
            elif delta < -math.pi:
                delta += 2 * math.pi
            total_angle_change += abs(delta)

        # If we've rotated at least 180 degrees (pi radians), it's circular
        return total_angle_change > math.pi

    def _is_alternating_motion(self, positions: List[Dict]) -> bool:
        """
        Detect if motion alternates (back and forth)

        Examples: shaking head, waving hand
        Requires significant and repeated reversals
        """
        if len(positions) < 8:
            return False

        # Check for direction reversals in primary axis
        # Calculate velocities in each direction
        velocities_x = []
        velocities_y = []
        velocities_z = []

        for i in range(1, len(positions)):
            prev = positions[i-1]
            curr = positions[i]
            velocities_x.append(curr['x'] - prev['x'])
            velocities_y.append(curr['y'] - prev['y'])
            velocities_z.append(curr['z'] - prev['z'])

        # Count significant sign changes (direction reversals)
        # Only count reversals where the velocity magnitude is significant
        threshold = 0.005  # Minimum velocity to count as movement

        reversals_x = sum(1 for i in range(1, len(velocities_x))
                         if velocities_x[i] * velocities_x[i-1] < 0 and
                         (abs(velocities_x[i]) > threshold or abs(velocities_x[i-1]) > threshold))
        reversals_y = sum(1 for i in range(1, len(velocities_y))
                         if velocities_y[i] * velocities_y[i-1] < 0 and
                         (abs(velocities_y[i]) > threshold or abs(velocities_y[i-1]) > threshold))
        reversals_z = sum(1 for i in range(1, len(velocities_z))
                         if velocities_z[i] * velocities_z[i-1] < 0 and
                         (abs(velocities_z[i]) > threshold or abs(velocities_z[i-1]) > threshold))

        # Require at least 3 significant reversals (4+ direction changes) for alternating
        # This ensures it's actually back-and-forth, not just one direction change
        return max(reversals_x, reversals_y, reversals_z) >= 3

    def _is_arc_motion(self, positions: List[Dict]) -> bool:
        """
        Detect if motion follows an arc (curved but not circular)

        Arc has consistent curvature but doesn't complete a circle
        """
        if len(positions) < 5:
            return False

        # Calculate curvature at each point
        # Curvature = change in direction angle / distance
        curvatures = []

        for i in range(1, len(positions) - 1):
            prev = positions[i-1]
            curr = positions[i]
            next_p = positions[i+1]

            # Vectors from curr to prev and curr to next
            v1 = (prev['x'] - curr['x'], prev['y'] - curr['y'])
            v2 = (next_p['x'] - curr['x'], next_p['y'] - curr['y'])

            # Angle between vectors
            dot = v1[0] * v2[0] + v1[1] * v2[1]
            mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
            mag2 = math.sqrt(v2[0]**2 + v2[1]**2)

            if mag1 > 0.001 and mag2 > 0.001:
                cos_angle = dot / (mag1 * mag2)
                # Clamp to [-1, 1] to avoid math domain error
                cos_angle = max(-1, min(1, cos_angle))
                angle = math.acos(cos_angle)
                curvatures.append(angle)

        if not curvatures:
            return False

        # Arc has consistent curvature (low variance)
        # and significant total curvature (> 30 degrees)
        mean_curvature = np.mean(curvatures)
        std_curvature = np.std(curvatures)
        total_curvature = sum(curvatures)

        # Consistent curvature
        consistent = (std_curvature / max(mean_curvature, 0.1)) < 0.5

        # Significant curvature (> 30 degrees = 0.52 radians)
        significant = total_curvature > 0.52

        return consistent and significant

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
