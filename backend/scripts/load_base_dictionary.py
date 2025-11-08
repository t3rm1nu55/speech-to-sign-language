"""
Load base ASL dictionary into database
"""

import json
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, Base, engine
from app.models.sign_dictionary import SignEntry

def load_base_dictionary():
    """Load base ASL dictionary from JSON file"""

    # Path to dictionary
    dict_file = Path(__file__).parent.parent / "data" / "asl_dictionary_base.json"

    if not dict_file.exists():
        print(f"Error: Dictionary file not found: {dict_file}")
        return 0

    # Load JSON
    with open(dict_file, 'r') as f:
        data = json.load(f)

    # Create tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    added = 0
    updated = 0

    # Process each category
    for category_name, signs in data['signs'].items():
        for sign_data in signs:
            word = sign_data['word'].lower()
            gloss = sign_data['gloss']
            category = sign_data['category']

            # Check if exists
            existing = db.query(SignEntry).filter(
                SignEntry.word == word,
                SignEntry.sign_language == 'ASL'
            ).first()

            if existing:
                # Update
                existing.gloss = gloss
                existing.category = category
                existing.is_verified = True
                existing.is_active = True
                updated += 1
            else:
                # Create new
                sign = SignEntry(
                    word=word,
                    sign_language='ASL',
                    gloss=gloss,
                    category=category,
                    is_verified=True,
                    is_active=True
                )
                db.add(sign)
                added += 1

            if (added + updated) % 50 == 0:
                db.commit()
                print(f"Processed {added + updated} signs...")

    db.commit()

    # Get total
    total = db.query(SignEntry).filter(SignEntry.sign_language == 'ASL').count()

    db.close()

    print(f"\n{'='*60}")
    print(f"BASE DICTIONARY LOADED")
    print(f"{'='*60}")
    print(f"Total signs in database: {total}")
    print(f"New signs added: {added}")
    print(f"Signs updated: {updated}")
    print(f"{'='*60}\n")

    return total

if __name__ == "__main__":
    load_base_dictionary()
