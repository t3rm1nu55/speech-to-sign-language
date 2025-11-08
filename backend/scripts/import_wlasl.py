"""
Import WLASL (Word-Level American Sign Language) dataset
Source: https://github.com/dxli94/WLASL
Dataset: 2,000 ASL signs with video references
"""

import os
import sys
import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, Base, engine
from app.models.sign_dictionary import SignEntry

class WLASLImporter:
    def __init__(self, json_path):
        self.json_path = json_path
        self.stats = {
            'total': 0,
            'added': 0,
            'updated': 0,
            'skipped': 0,
            'with_video': 0
        }

    def load_wlasl_data(self):
        """Load WLASL JSON file"""
        logger.info(f"Loading WLASL data from {self.json_path}")

        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f"Loaded {len(data)} ASL signs from WLASL")
        return data

    def get_primary_video_url(self, instances):
        """
        Get the best video URL from instances
        Priority: train split > high quality > first available
        """
        if not instances:
            return None

        # Try to find a training split video first
        train_instances = [i for i in instances if i.get('split') == 'train']

        if train_instances:
            # Prefer certain sources
            preferred_sources = ['aslsignbank', 'aslbrick', 'valencia-asl']
            for source in preferred_sources:
                for instance in train_instances:
                    if instance.get('source') == source and instance.get('url'):
                        return instance['url']

            # Return first train instance with URL
            for instance in train_instances:
                if instance.get('url'):
                    return instance['url']

        # Fallback to any instance with URL
        for instance in instances:
            if instance.get('url'):
                return instance['url']

        return None

    def categorize_word(self, gloss):
        """
        Simple categorization based on common patterns
        This is basic - could be enhanced with NLP
        """
        gloss_lower = gloss.lower()

        # Question words
        if gloss_lower in ['who', 'what', 'where', 'when', 'why', 'how', 'which']:
            return 'question'

        # Common verbs (simplified list)
        verbs = ['go', 'make', 'do', 'have', 'be', 'see', 'know', 'think',
                'help', 'need', 'want', 'eat', 'drink', 'sleep', 'work',
                'play', 'read', 'write', 'speak', 'listen', 'watch', 'buy',
                'sell', 'teach', 'learn', 'give', 'take', 'send', 'receive']
        if gloss_lower in verbs or gloss_lower.endswith('ing'):
            return 'verb'

        # Pronouns
        if gloss_lower in ['i', 'you', 'he', 'she', 'we', 'they', 'my', 'your', 'his', 'her', 'our', 'their']:
            return 'pronoun'

        # Adjectives (common patterns)
        adjectives = ['good', 'bad', 'happy', 'sad', 'big', 'small', 'hot', 'cold',
                     'fast', 'slow', 'easy', 'hard', 'beautiful', 'ugly', 'clean', 'dirty']
        if gloss_lower in adjectives:
            return 'adjective'

        # Default to noun
        return 'noun'

    def import_sign(self, db, gloss_data):
        """Import a single sign entry"""
        gloss = gloss_data.get('gloss', '').strip()

        if not gloss:
            self.stats['skipped'] += 1
            return

        word = gloss.lower()
        instances = gloss_data.get('instances', [])

        # Get primary video URL
        video_url = self.get_primary_video_url(instances)

        # Check if sign already exists
        existing = db.query(SignEntry).filter(
            SignEntry.word == word,
            SignEntry.sign_language == 'ASL'
        ).first()

        # Prepare sign data
        sign_data = {
            'word': word,
            'sign_language': 'ASL',
            'gloss': gloss.upper(),
            'category': self.categorize_word(gloss),
            'video_url': video_url,
            'is_verified': True,  # WLASL is a verified dataset
            'is_active': True,
            'regional_variations': json.dumps({
                'wlasl_instances': len(instances),
                'sources': list(set(i.get('source', 'unknown') for i in instances))
            }) if instances else None
        }

        if existing:
            # Update if we have a video URL and existing doesn't, or always update from WLASL
            if video_url:
                for key, value in sign_data.items():
                    if value is not None:  # Only update non-null values
                        setattr(existing, key, value)
                self.stats['updated'] += 1
                if video_url:
                    self.stats['with_video'] += 1
            else:
                self.stats['skipped'] += 1
        else:
            # Create new entry
            sign = SignEntry(**sign_data)
            db.add(sign)
            self.stats['added'] += 1
            if video_url:
                self.stats['with_video'] += 1

        self.stats['total'] += 1

    def import_all(self):
        """Import all WLASL signs to database"""
        logger.info("=" * 60)
        logger.info("WLASL DATASET IMPORT")
        logger.info("=" * 60)

        # Create tables
        Base.metadata.create_all(bind=engine)

        # Load data
        wlasl_data = self.load_wlasl_data()

        # Import to database
        db = SessionLocal()

        try:
            for idx, gloss_data in enumerate(wlasl_data):
                self.import_sign(db, gloss_data)

                # Commit in batches
                if (idx + 1) % 100 == 0:
                    db.commit()
                    logger.info(f"Processed {idx + 1}/{len(wlasl_data)} signs...")

            # Final commit
            db.commit()

            # Get final count
            total_signs = db.query(SignEntry).filter(SignEntry.sign_language == 'ASL').count()

            logger.info("\n" + "=" * 60)
            logger.info("WLASL IMPORT COMPLETE")
            logger.info("=" * 60)
            logger.info(f"Total signs processed: {self.stats['total']}")
            logger.info(f"New signs added: {self.stats['added']}")
            logger.info(f"Signs updated: {self.stats['updated']}")
            logger.info(f"Signs skipped: {self.stats['skipped']}")
            logger.info(f"Signs with video URLs: {self.stats['with_video']}")
            logger.info(f"Total ASL signs in database: {total_signs}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error during import: {str(e)}")
            import traceback
            traceback.print_exc()
            db.rollback()
        finally:
            db.close()

        return self.stats

def main():
    """Main function"""
    # Path to WLASL JSON file
    wlasl_json = Path(__file__).parent.parent / "data" / "wlasl_repo" / "start_kit" / "WLASL_v0.3.json"

    if not wlasl_json.exists():
        logger.error(f"WLASL JSON file not found: {wlasl_json}")
        logger.error("Please clone the WLASL repository first:")
        logger.error("  cd backend/data")
        logger.error("  git clone https://github.com/dxli94/WLASL.git wlasl_repo")
        sys.exit(1)

    # Import WLASL data
    importer = WLASLImporter(wlasl_json)
    stats = importer.import_all()

    logger.info(f"\n✓ Successfully imported {stats['added']} new signs from WLASL!")

if __name__ == "__main__":
    main()
