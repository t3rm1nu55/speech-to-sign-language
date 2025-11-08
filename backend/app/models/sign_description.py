"""
ASL Sign Description Models
Based on the 5 parameters of ASL linguistics: Handshape, Location, Movement, Palm Orientation, Non-Manual Markers
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum


class Handshape(str, Enum):
    """Standard ASL handshapes"""
    # Numbers
    ONE = "1"  # Index finger extended
    TWO = "2"  # Index and middle extended
    THREE = "3"  # Thumb, index, middle extended
    FOUR = "4"  # Four fingers extended, thumb tucked
    FIVE = "5"  # All fingers extended (open hand)
    SIX = "6"  # Three fingers extended, thumb and pinky touch
    SEVEN = "7"  # Four fingers extended in 7 shape
    EIGHT = "8"  # Index and middle touch thumb
    NINE = "9"  # Index and thumb form circle, others extended
    ZERO = "0"  # Thumb and index form O, others closed

    # Letters (common handshapes)
    A = "A"  # Closed fist, thumb to side
    B = "B"  # Flat hand, fingers together, thumb across palm
    C = "C"  # Curved hand forming C shape
    D = "D"  # Index up, thumb touches middle/ring/pinky
    E = "E"  # Fingers curl to touch thumb pad
    F = "F"  # Index and thumb touch in circle, other fingers extended
    G = "G"  # Index and thumb extended sideways
    H = "H"  # Index and middle extended sideways
    I = "I"  # Pinky extended
    K = "K"  # Index and middle up, thumb touches middle
    L = "L"  # Index and thumb form L shape
    M = "M"  # Thumb under first three fingers
    N = "N"  # Thumb under first two fingers
    O = "O"  # Fingers and thumb forming circle
    R = "R"  # Index and middle crossed
    S = "S"  # Fist with thumb in front
    T = "T"  # Thumb between index and middle
    U = "U"  # Index and middle together, extended up
    V = "V"  # Index and middle spread in V
    W = "W"  # Three fingers (index, middle, ring) extended
    X = "X"  # Index bent in hook shape
    Y = "Y"  # Thumb and pinky extended

    # Functional shapes
    FIST = "fist"  # Closed fist
    FLAT = "flat"  # Flat open palm
    CLAW = "claw"  # All fingers curved
    BENT = "bent"  # Fingers bent at middle joint
    INDEX = "index"  # Only index finger extended
    POINT = "point"  # Index finger pointing

    # Special shapes
    ILY = "ILY"  # I-Love-You (thumb, index, pinky extended)
    HORNS = "horns"  # Index and pinky extended

    UNKNOWN = "unknown"


class Location(str, Enum):
    """Where the sign is made in signing space"""
    # Face regions
    FOREHEAD = "forehead"
    TEMPLE = "temple"
    EYE = "eye"
    NOSE = "nose"
    CHEEK = "cheek"
    MOUTH = "mouth"
    CHIN = "chin"

    # Head regions
    EAR = "ear"
    NECK = "neck"

    # Upper body
    SHOULDER = "shoulder"
    CHEST = "chest"
    STOMACH = "stomach"

    # Signing space
    NEUTRAL_SPACE = "neutral_space"  # In front of chest
    HIGH_SPACE = "high_space"  # Above shoulder level
    LOW_SPACE = "low_space"  # Below chest level

    # Relative to other hand
    OTHER_HAND = "other_hand"

    # Sides
    SIDE_LEFT = "side_left"
    SIDE_RIGHT = "side_right"

    UNKNOWN = "unknown"


class Movement(str, Enum):
    """How the hand moves"""
    # Basic movements
    NONE = "none"  # Static sign
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    FORWARD = "forward"
    BACKWARD = "backward"

    # Circular
    CIRCLE = "circle"
    CIRCLE_CW = "circle_clockwise"
    CIRCLE_CCW = "circle_counterclockwise"

    # Oscillating
    SHAKE = "shake"  # Side to side
    NOD = "nod"  # Up and down
    WIGGLE = "wiggle"  # Fingers wiggle

    # Complex
    TAP = "tap"  # Tap contact location
    BRUSH = "brush"  # Brush across surface
    ARC = "arc"  # Arc movement
    ZIGZAG = "zigzag"
    TWIST = "twist"  # Wrist rotation

    # Opening/Closing
    OPEN = "open"  # Hand opens
    CLOSE = "close"  # Hand closes

    # Contact
    CONTACT = "contact"  # Makes contact
    DOUBLE_CONTACT = "double_contact"  # Two taps

    # Alternating
    ALTERNATING = "alternating"  # Two hands alternate

    UNKNOWN = "unknown"


class PalmOrientation(str, Enum):
    """Direction the palm faces"""
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    FORWARD = "forward"  # Away from signer
    BACKWARD = "backward"  # Toward signer
    IN = "in"  # Toward body
    OUT = "out"  # Away from body

    UNKNOWN = "unknown"


class NonManualMarker(str, Enum):
    """Facial expressions and body movements"""
    # Grammatical
    EYEBROWS_RAISED = "eyebrows_raised"  # Questions, topics
    EYEBROWS_FURROWED = "eyebrows_furrowed"  # WH-questions
    HEAD_SHAKE = "head_shake"  # Negation
    HEAD_NOD = "head_nod"  # Affirmation
    HEAD_TILT = "head_tilt"

    # Emotional
    SMILE = "smile"
    FROWN = "frown"

    # Mouth morphemes
    MOUTH_OPEN = "mouth_open"
    LIPS_PRESSED = "lips_pressed"
    TONGUE_OUT = "tongue_out"

    # Body
    BODY_LEAN_FORWARD = "body_lean_forward"
    BODY_LEAN_BACK = "body_lean_back"
    SHOULDER_SHIFT = "shoulder_shift"

    NONE = "none"
    UNKNOWN = "unknown"


class HandConfiguration(BaseModel):
    """Complete description of one hand's configuration"""
    handshape: Handshape
    location: Location
    palm_orientation: PalmOrientation
    fingers_extended: Optional[List[str]] = Field(
        default=None,
        description="Which fingers are extended: thumb, index, middle, ring, pinky"
    )


class SignDescription(BaseModel):
    """
    Complete linguistic description of an ASL sign using the 5 parameters
    """
    gloss: str = Field(..., description="ASL gloss (uppercase word)")
    english_word: str = Field(..., description="English translation")

    # Core 5 parameters
    dominant_hand: HandConfiguration
    non_dominant_hand: Optional[HandConfiguration] = None
    movement: Movement
    non_manual_markers: List[NonManualMarker] = Field(default_factory=list)

    # Additional context
    is_two_handed: bool = False
    symmetrical: bool = Field(
        default=False,
        description="True if both hands have same shape/movement"
    )

    # Temporal information
    duration_frames: Optional[int] = Field(
        default=None,
        description="Typical duration in frames at 30fps"
    )

    # Movement details
    movement_path: Optional[str] = Field(
        default=None,
        description="Detailed description of movement path"
    )

    # Contact points
    contact_location: Optional[Location] = None

    # Descriptive notes
    notes: Optional[str] = Field(
        default=None,
        description="Additional linguistic or visual notes"
    )

    # Validation metadata
    source: Optional[str] = Field(
        default=None,
        description="Source of this description (ASL dictionary, linguistic research, etc.)"
    )
    verified: bool = Field(
        default=False,
        description="Has this description been validated against video?"
    )


class SignValidationResult(BaseModel):
    """Result of validating a sign interpretation against expected description"""
    gloss: str
    video_url: str

    # Overall validation
    passed: bool
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="Overall confidence in interpretation (0-1)"
    )

    # Feature-level validation
    handshape_match: Optional[bool] = None
    handshape_confidence: Optional[float] = None

    location_match: Optional[bool] = None
    location_confidence: Optional[float] = None

    movement_match: Optional[bool] = None
    movement_confidence: Optional[float] = None

    palm_orientation_match: Optional[bool] = None
    palm_orientation_confidence: Optional[float] = None

    # Diagnostic information
    issues_found: List[str] = Field(default_factory=list)
    diagnostics: Dict[str, str] = Field(default_factory=dict)

    # Video quality metrics
    video_quality_score: Optional[float] = None
    frame_count: Optional[int] = None
    pose_detection_rate: Optional[float] = Field(
        default=None,
        description="Percentage of frames where pose was detected"
    )

    # Improvement suggestions
    suggestions: List[str] = Field(default_factory=list)

    # Expected vs actual
    expected_description: Optional[SignDescription] = None
    extracted_features: Optional[Dict] = None


class ValidationReport(BaseModel):
    """Comprehensive validation report for multiple signs"""
    total_signs_tested: int
    passed_count: int
    failed_count: int
    average_confidence: float

    # Category breakdown
    handshape_accuracy: float
    location_accuracy: float
    movement_accuracy: float
    palm_accuracy: float

    # Per-sign results
    sign_results: List[SignValidationResult]

    # Framework issues
    framework_issues: List[str] = Field(
        default_factory=list,
        description="Issues found with the descriptive framework itself"
    )

    # Improvement recommendations
    recommendations: List[str] = Field(default_factory=list)

    # Iteration metadata
    iteration_number: int = 1
    date_tested: str
