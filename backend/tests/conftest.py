"""
Pytest configuration and fixtures
"""

import pytest
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from main import app

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    """Create test database"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db):
    """Create test client"""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def sample_audio_data():
    """Sample base64 encoded audio data for testing"""
    # This is a minimal WAV file header + silence
    # In real tests, you'd use actual audio
    import base64
    # Minimal WAV file (1 second of silence at 16kHz, 16-bit mono)
    wav_header = bytes([
        0x52, 0x49, 0x46, 0x46,  # "RIFF"
        0x24, 0x00, 0x00, 0x00,  # File size - 8
        0x57, 0x41, 0x56, 0x45,  # "WAVE"
        0x66, 0x6d, 0x74, 0x20,  # "fmt "
        0x10, 0x00, 0x00, 0x00,  # Subchunk size (16)
        0x01, 0x00,              # Audio format (1 = PCM)
        0x01, 0x00,              # Num channels (1)
        0x80, 0x3e, 0x00, 0x00,  # Sample rate (16000)
        0x00, 0x7d, 0x00, 0x00,  # Byte rate
        0x02, 0x00,              # Block align
        0x10, 0x00,              # Bits per sample (16)
        0x64, 0x61, 0x74, 0x61,  # "data"
        0x00, 0x00, 0x00, 0x00,  # Data size
    ])
    return base64.b64encode(wav_header).decode('utf-8')

@pytest.fixture
def test_transcripts():
    """Common test transcripts with expected translations"""
    return [
        {
            "text": "Hello",
            "expected_signs": ["HELLO"],
            "sign_language": "ASL"
        },
        {
            "text": "How are you?",
            "expected_contains": ["HOW", "YOU"],
            "sign_language": "ASL"
        },
        {
            "text": "Thank you",
            "expected_signs": ["THANK-YOU"],
            "sign_language": "ASL"
        },
        {
            "text": "I need help",
            "expected_contains": ["I", "NEED", "HELP"],
            "sign_language": "ASL"
        }
    ]
