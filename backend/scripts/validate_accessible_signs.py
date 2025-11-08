"""
Focused validation on accessible ASL Bricks videos
Tests only signs where we have both descriptions and accessible videos
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import json
from datetime import datetime
from app.database import SessionLocal
from app.models.sign_dictionary import SignEntry
from app.models.sign_description import SignDescription
from app.services.sign_validation import SignValidationService
from app.services.pose_extraction import PoseExtractionService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run validation on accessible signs"""

    db = SessionLocal()
    validation_service = SignValidationService()
    pose_service = PoseExtractionService()

    print("="*80)
    print("FOCUSED VALIDATION - ACCESSIBLE VIDEOS ONLY")
    print("="*80)
    print()

    # Find signs with ASL Bricks videos that we have descriptions for
    test_signs = ["GOOD", "PLEASE", "SAD", "NEW", "HARD", "PRETTY", "SLEEP", "HEAD"]

    print(f"Testing {len(test_signs)} signs with accessible ASL Bricks videos\n")

    results = []

    for gloss in test_signs:
        # Get video URL
        entry = db.query(SignEntry).filter(
            SignEntry.gloss == gloss.upper(),
            SignEntry.video_url.like('%aslbricks%')
        ).first()

        if not entry:
            entry = db.query(SignEntry).filter(
                SignEntry.word == gloss.lower(),
                SignEntry.video_url.like('%aslbricks%')
            ).first()

        if not entry:
            print(f"❌ {gloss}: No ASL Bricks video found")
            continue

        video_url = entry.video_url

        print(f"\n{'─'*80}")
        print(f"Testing: {gloss}")
        print(f"URL: {video_url}")

        # Extract pose (quick test with max 10 frames)
        try:
            pose_data = pose_service.extract_pose_from_video(video_url, max_frames=10)

            if pose_data.get('success'):
                frames = pose_data.get('frames', [])
                fps = pose_data.get('fps', 0)

                print(f"✅ Pose extracted successfully")
                print(f"   Frames: {len(frames)}")
                print(f"   FPS: {fps:.1f}")

                # Check if we have pose landmarks
                if frames and len(frames) > 0:
                    frame = frames[0]
                    has_pose = frame.get('pose') is not None and len(frame.get('pose', [])) >= 33
                    has_hands = (frame.get('left_hand') is not None or frame.get('right_hand') is not None)

                    print(f"   Body pose detected: {'✅' if has_pose else '❌'}")
                    print(f"   Hands detected: {'✅' if has_hands else '❌'}")

                    # Analyze features
                    features = validation_service._extract_sign_features(frames)

                    print(f"\n   Extracted Features:")
                    print(f"      Handshape: {features.get('handshape', 'unknown')}")
                    print(f"      Location: {features.get('location', 'unknown')}")
                    print(f"      Movement: {features.get('movement', 'unknown')}")

                    if features.get('hand_velocity'):
                        print(f"      Hand velocity: {features['hand_velocity']:.4f}")

                    results.append({
                        'gloss': gloss,
                        'success': True,
                        'frames': len(frames),
                        'features': features
                    })

                else:
                    print(f"   ⚠️  Frames extracted but no landmarks detected")
                    results.append({
                        'gloss': gloss,
                        'success': False,
                        'error': 'No landmarks in frames'
                    })

            else:
                print(f"❌ Pose extraction failed: {pose_data.get('error', 'Unknown')}")
                results.append({
                    'gloss': gloss,
                    'success': False,
                    'error': pose_data.get('error', 'Unknown')
                })

        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            results.append({
                'gloss': gloss,
                'success': False,
                'error': str(e)
            })

        # Small delay
        await asyncio.sleep(0.5)

    # Summary
    print(f"\n{'='*80}")
    print("VALIDATION SUMMARY")
    print(f"{'='*80}")

    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]

    print(f"\nTotal tested: {len(results)}")
    print(f"✅ Successful: {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
    print(f"❌ Failed: {len(failed)} ({len(failed)/len(results)*100:.1f}%)")

    if successful:
        print(f"\n✅ Successfully validated signs:")
        for result in successful:
            features = result.get('features', {})
            print(f"   {result['gloss']}: {features.get('handshape', '?')} @ {features.get('location', '?')} → {features.get('movement', '?')}")

    if failed:
        print(f"\n❌ Failed signs:")
        for result in failed:
            print(f"   {result['gloss']}: {result.get('error', 'Unknown error')}")

    print(f"\n{'='*80}")
    print("KEY FINDINGS:")
    print(f"{'='*80}")

    if len(successful) > 0:
        print(f"\n✅ ASL Bricks videos are WORKING!")
        print(f"   - {len(successful)} signs successfully processed")
        print(f"   - Pose extraction operational")
        print(f"   - Feature detection working")
        print(f"\n💡 Next steps:")
        print(f"   1. Add descriptions for more ASL Bricks signs")
        print(f"   2. Run full validation with expected vs detected comparison")
        print(f"   3. Refine feature detection algorithms based on results")
    else:
        print(f"\n⚠️  No signs successfully processed")
        print(f"   Check MediaPipe configuration and video processing")

    db.close()


if __name__ == "__main__":
    import os
    if 'DATABASE_URL' not in os.environ:
        os.environ['DATABASE_URL'] = 'sqlite:///./sign_language.db'

    asyncio.run(main())
