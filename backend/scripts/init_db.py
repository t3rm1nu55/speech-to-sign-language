"""
Initialize database with sample sign language dictionary data
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
from app.models.sign_dictionary import SignEntry, SignPhrase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables():
    """Create all database tables"""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created successfully")

def add_sample_signs():
    """Add sample sign language dictionary entries"""
    db = SessionLocal()

    try:
        # Check if data already exists
        existing = db.query(SignEntry).first()
        if existing:
            logger.info("Sample data already exists, skipping...")
            return

        logger.info("Adding sample sign language entries...")

        # Sample ASL signs
        sample_signs = [
            {
                "word": "hello",
                "sign_language": "ASL",
                "gloss": "HELLO",
                "category": "greeting",
                "handshape": "flat-hand",
                "location": "forehead",
                "movement": "forward"
            },
            {
                "word": "thank you",
                "sign_language": "ASL",
                "gloss": "THANK-YOU",
                "category": "greeting",
                "handshape": "flat-hand",
                "location": "chin",
                "movement": "forward-down"
            },
            {
                "word": "please",
                "sign_language": "ASL",
                "gloss": "PLEASE",
                "category": "polite",
                "handshape": "flat-hand",
                "location": "chest",
                "movement": "circular"
            },
            {
                "word": "yes",
                "sign_language": "ASL",
                "gloss": "YES",
                "category": "response",
                "handshape": "fist",
                "location": "neutral",
                "movement": "up-down"
            },
            {
                "word": "no",
                "sign_language": "ASL",
                "gloss": "NO",
                "category": "response",
                "handshape": "index-middle",
                "location": "neutral",
                "movement": "snap"
            },
            {
                "word": "help",
                "sign_language": "ASL",
                "gloss": "HELP",
                "category": "request",
                "handshape": "fist",
                "location": "chest",
                "movement": "up"
            },
            {
                "word": "sorry",
                "sign_language": "ASL",
                "gloss": "SORRY",
                "category": "polite",
                "handshape": "fist",
                "location": "chest",
                "movement": "circular"
            },
            {
                "word": "good",
                "sign_language": "ASL",
                "gloss": "GOOD",
                "category": "adjective",
                "handshape": "flat-hand",
                "location": "chin",
                "movement": "forward-down"
            },
            {
                "word": "bad",
                "sign_language": "ASL",
                "gloss": "BAD",
                "category": "adjective",
                "handshape": "flat-hand",
                "location": "chin",
                "movement": "forward-rotate"
            },
            {
                "word": "understand",
                "sign_language": "ASL",
                "gloss": "UNDERSTAND",
                "category": "verb",
                "handshape": "index",
                "location": "forehead",
                "movement": "flick-up"
            }
        ]

        for sign_data in sample_signs:
            sign = SignEntry(**sign_data, is_verified=True)
            db.add(sign)

        # Sample common phrases
        sample_phrases = [
            {
                "text": "How are you?",
                "sign_language": "ASL",
                "gloss_sequence": "HOW YOU",
                "category": "greeting"
            },
            {
                "text": "Nice to meet you",
                "sign_language": "ASL",
                "gloss_sequence": "NICE MEET YOU",
                "category": "greeting"
            },
            {
                "text": "What is your name?",
                "sign_language": "ASL",
                "gloss_sequence": "YOUR NAME WHAT",
                "category": "question"
            }
        ]

        for phrase_data in sample_phrases:
            phrase = SignPhrase(**phrase_data)
            db.add(phrase)

        db.commit()
        logger.info(f"Added {len(sample_signs)} sample signs and {len(sample_phrases)} phrases")

    except Exception as e:
        logger.error(f"Error adding sample data: {str(e)}")
        db.rollback()
    finally:
        db.close()

def main():
    """Main initialization function"""
    logger.info("Starting database initialization...")

    # Create tables
    create_tables()

    # Add sample data
    add_sample_signs()

    logger.info("Database initialization complete!")

if __name__ == "__main__":
    main()
