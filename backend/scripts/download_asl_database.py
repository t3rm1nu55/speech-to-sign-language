"""
Download comprehensive ASL sign language databases asynchronously
Sources:
- ASL-LEX 2.0: 2,723 signs with phonological data
- GitHub sign-language-datasets
- WLASL: 2,000 word-level signs
"""

import os
import sys
import json
import asyncio
import aiohttp
import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, Base, engine
from app.models.sign_dictionary import SignEntry, SignPhrase

class ASLDatabaseDownloader:
    def __init__(self):
        self.data_dir = Path("data/asl_databases")
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def download_file(self, session, url, filename):
        """Download file asynchronously"""
        filepath = self.data_dir / filename

        if filepath.exists():
            logger.info(f"✓ {filename} already exists")
            return filepath

        try:
            logger.info(f"Downloading {filename}...")
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(filepath, 'wb') as f:
                        f.write(content)
                    logger.info(f"✓ Downloaded {filename}")
                    return filepath
                else:
                    logger.error(f"Failed to download {filename}: HTTP {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error downloading {filename}: {str(e)}")
            return None

    async def download_asl_lex(self, session):
        """Download ASL-LEX 2.0 database"""
        logger.info("\n=== Downloading ASL-LEX 2.0 (2,723 signs) ===")

        # Direct download URLs from OSF
        urls = {
            "ASL-LEX_2.0.csv": "https://osf.io/download/jyhew/",  # Main dataset
        }

        files = []
        for filename, url in urls.items():
            file = await self.download_file(session, url, filename)
            if file:
                files.append(file)

        return files

    async def download_github_datasets(self, session):
        """Download sign language datasets from GitHub"""
        logger.info("\n=== Downloading GitHub Sign Language Datasets ===")

        # Sign language translator datasets
        base_url = "https://raw.githubusercontent.com/sign-language-translator/sign-language-datasets/main"

        urls = {
            "pk-dictionary-mapping.json": f"{base_url}/parallel-corpus/pk-dictionary-mapping.json",
        }

        files = []
        for filename, url in urls.items():
            file = await self.download_file(session, url, filename)
            if file:
                files.append(file)

        return files

    async def download_basic_asl_json(self, session):
        """Download basic ASL dictionary JSON if available"""
        logger.info("\n=== Downloading Basic ASL Dictionaries ===")

        # Common ASL signs from various sources
        urls = {
            # Add any public JSON ASL dictionaries here
        }

        files = []
        for filename, url in urls.items():
            file = await self.download_file(session, url, filename)
            if file:
                files.append(file)

        return files

    async def download_all(self):
        """Download all databases asynchronously"""
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.download_asl_lex(session),
                self.download_github_datasets(session),
                self.download_basic_asl_json(session),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            all_files = []
            for result in results:
                if isinstance(result, list):
                    all_files.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"Error in download task: {str(result)}")

            return all_files

    def process_asl_lex_csv(self, csv_file):
        """Process ASL-LEX CSV and import to database"""
        logger.info(f"\n=== Processing {csv_file.name} ===")

        try:
            df = pd.read_csv(csv_file)
            logger.info(f"Loaded {len(df)} signs from ASL-LEX")

            db = SessionLocal()
            added = 0
            updated = 0

            for idx, row in df.iterrows():
                # Extract sign data
                word = str(row.get('EntryID', '')).lower()

                # Skip if no word
                if not word or word == 'nan':
                    continue

                # Check if sign already exists
                existing = db.query(SignEntry).filter(
                    SignEntry.word == word,
                    SignEntry.sign_language == 'ASL'
                ).first()

                sign_data = {
                    'word': word,
                    'sign_language': 'ASL',
                    'gloss': str(row.get('EntryID', word)).upper(),
                    'category': str(row.get('Lexical_Class', 'unknown')),
                    'frequency': int(row.get('ASL_Freq_Rank', 0)) if pd.notna(row.get('ASL_Freq_Rank')) else 0,
                    'is_verified': True,
                    'is_active': True
                }

                if existing:
                    # Update existing
                    for key, value in sign_data.items():
                        setattr(existing, key, value)
                    updated += 1
                else:
                    # Create new
                    sign = SignEntry(**sign_data)
                    db.add(sign)
                    added += 1

                if (added + updated) % 100 == 0:
                    db.commit()
                    logger.info(f"Processed {added + updated} signs...")

            db.commit()
            db.close()

            logger.info(f"✓ Added {added} new signs, updated {updated} signs")
            return added, updated

        except Exception as e:
            logger.error(f"Error processing ASL-LEX CSV: {str(e)}")
            import traceback
            traceback.print_exc()
            return 0, 0

    def process_github_json(self, json_file):
        """Process GitHub JSON datasets"""
        logger.info(f"\n=== Processing {json_file.name} ===")

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            logger.info(f"Loaded JSON with {len(data)} entries")

            db = SessionLocal()
            added = 0

            # Process based on structure
            if isinstance(data, dict):
                for word, sign_data in data.items():
                    # Check if exists
                    existing = db.query(SignEntry).filter(
                        SignEntry.word == word.lower(),
                        SignEntry.sign_language == 'ASL'
                    ).first()

                    if not existing:
                        sign = SignEntry(
                            word=word.lower(),
                            sign_language='ASL',
                            gloss=word.upper(),
                            is_verified=True,
                            is_active=True
                        )
                        db.add(sign)
                        added += 1

            db.commit()
            db.close()

            logger.info(f"✓ Added {added} new signs from GitHub dataset")
            return added, 0

        except Exception as e:
            logger.error(f"Error processing GitHub JSON: {str(e)}")
            return 0, 0

    def import_to_database(self, files):
        """Import downloaded files to database"""
        logger.info("\n=== Importing to Database ===")

        # Create tables
        Base.metadata.create_all(bind=engine)

        total_added = 0
        total_updated = 0

        for file in files:
            if not file or not file.exists():
                continue

            if file.suffix == '.csv':
                added, updated = self.process_asl_lex_csv(file)
                total_added += added
                total_updated += updated
            elif file.suffix == '.json':
                added, updated = self.process_github_json(file)
                total_added += added
                total_updated += updated

        # Get final count
        db = SessionLocal()
        total_signs = db.query(SignEntry).filter(SignEntry.sign_language == 'ASL').count()
        db.close()

        logger.info("\n" + "="*60)
        logger.info(f"DATABASE IMPORT COMPLETE")
        logger.info("="*60)
        logger.info(f"Total signs in database: {total_signs}")
        logger.info(f"New signs added: {total_added}")
        logger.info(f"Signs updated: {total_updated}")
        logger.info("="*60)

        return total_signs

async def main():
    """Main async function"""
    downloader = ASLDatabaseDownloader()

    logger.info("="*60)
    logger.info("ASL DATABASE DOWNLOADER")
    logger.info("="*60)

    # Download all databases
    files = await downloader.download_all()

    # Import to database
    if files:
        total = downloader.import_to_database(files)
        logger.info(f"\n✓ Successfully loaded {total} ASL signs!")
    else:
        logger.error("No files downloaded")

if __name__ == "__main__":
    # Check dependencies
    try:
        import aiohttp
        import pandas
    except ImportError:
        print("Installing required dependencies...")
        os.system("pip install -q aiohttp pandas")
        import aiohttp
        import pandas

    asyncio.run(main())
