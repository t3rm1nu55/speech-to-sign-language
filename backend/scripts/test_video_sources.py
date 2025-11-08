"""
Quick diagnostic script to test which video sources are accessible
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models.sign_dictionary import SignEntry
from app.services.pose_extraction import PoseExtractionService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_video_sources():
    """Test video accessibility from different sources"""

    db = SessionLocal()
    pose_service = PoseExtractionService()

    print("=" * 80)
    print("VIDEO SOURCE ACCESSIBILITY TEST")
    print("=" * 80)
    print()

    # Test different video sources
    test_signs = [
        ("HELLO", None),
        ("GOOD", None),
        ("PLEASE", None),
        ("YES", None),
        ("WATER", None),
    ]

    results = {}

    for gloss, _ in test_signs:
        # Get video URL from database
        entry = db.query(SignEntry).filter(
            SignEntry.gloss == gloss.upper(),
            SignEntry.video_url.isnot(None)
        ).first()

        if not entry:
            entry = db.query(SignEntry).filter(
                SignEntry.word == gloss.lower(),
                SignEntry.video_url.isnot(None)
            ).first()

        if not entry:
            print(f"❌ {gloss}: No video in database")
            continue

        video_url = entry.video_url

        # Determine source
        if 'youtube.com' in video_url or 'youtu.be' in video_url:
            source = "YouTube"
        elif 'aslsignbank' in video_url or 'signbank' in video_url:
            source = "ASL SignBank"
        elif 'aslbricks' in video_url:
            source = "ASL Bricks"
        elif 'handspeak' in video_url:
            source = "Handspeak"
        else:
            source = "Other"

        # Try to extract pose (just 1 frame to test accessibility)
        print(f"\n{'─'*80}")
        print(f"Testing: {gloss}")
        print(f"Source: {source}")
        print(f"URL: {video_url[:80]}...")

        try:
            result = pose_service.extract_pose_from_video(video_url, max_frames=1)

            if result.get('success'):
                print(f"✅ SUCCESS - Downloaded and processed")
                print(f"   FPS: {result.get('fps', 0):.1f}")
                print(f"   Frames extracted: {result.get('processed_frames', 0)}")

                if source not in results:
                    results[source] = {'success': 0, 'failed': 0}
                results[source]['success'] += 1
            else:
                print(f"❌ FAILED - {result.get('error', 'Unknown error')}")

                if source not in results:
                    results[source] = {'success': 0, 'failed': 0}
                results[source]['failed'] += 1

        except Exception as e:
            print(f"❌ EXCEPTION - {str(e)}")
            if source not in results:
                results[source] = {'success': 0, 'failed': 0}
            results[source]['failed'] += 1

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY BY SOURCE")
    print(f"{'='*80}")

    for source, stats in results.items():
        total = stats['success'] + stats['failed']
        success_rate = (stats['success'] / total * 100) if total > 0 else 0

        print(f"\n{source}:")
        print(f"  Success: {stats['success']}/{total} ({success_rate:.1f}%)")
        if stats['success'] > 0:
            print(f"  ✅ This source is ACCESSIBLE")
        else:
            print(f"  ❌ This source is NOT accessible")

    print(f"\n{'='*80}")
    print("RECOMMENDATIONS:")
    print(f"{'='*80}")

    # Find best sources
    accessible_sources = [s for s, stats in results.items() if stats['success'] > 0]

    if accessible_sources:
        print(f"\n✅ Use videos from: {', '.join(accessible_sources)}")
        print(f"   Update validation to prioritize these sources")
    else:
        print(f"\n⚠️  No video sources currently accessible")
        print(f"   Options:")
        print(f"   1. Use local video files for testing")
        print(f"   2. Create mock/synthetic test data")
        print(f"   3. Find alternative public ASL video datasets")

    db.close()


if __name__ == "__main__":
    import os
    if 'DATABASE_URL' not in os.environ:
        os.environ['DATABASE_URL'] = 'sqlite:///./sign_language.db'

    test_video_sources()
