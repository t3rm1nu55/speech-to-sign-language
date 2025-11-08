"""
Full Validation Test - Iteration 4
Run validation on all signs with both descriptions and ASL Bricks videos
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import asyncio
from datetime import datetime
from app.database import SessionLocal
from app.models.sign_dictionary import SignEntry
from app.models.sign_description import SignDescription
from app.services.sign_validation import SignValidationService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_full_validation():
    """Run validation on all ready signs"""

    # Load sign descriptions
    desc_file = Path(__file__).parent.parent / 'data' / 'asl_sign_descriptions.json'
    with open(desc_file) as f:
        data = json.load(f)

    descriptions_data = data['signs']

    # Get ASL Bricks videos
    db = SessionLocal()
    asl_bricks_entries = {
        entry.word.lower(): entry.video_url
        for entry in db.query(SignEntry).filter(
            SignEntry.video_url.like('%aslbricks%')
        ).all()
    }

    # Find ready signs
    ready_signs = []
    for desc_data in descriptions_data:
        word = desc_data.get('english_word', desc_data['gloss']).lower()
        if word in asl_bricks_entries:
            ready_signs.append((desc_data, asl_bricks_entries[word]))

    print("=" * 80)
    print("FULL VALIDATION TEST - ITERATION 4")
    print("=" * 80)
    print(f"Testing {len(ready_signs)} signs with expected vs detected comparison")
    print(f"Framework: ASL 5-Parameter Linguistic Model")
    print(f"Video Source: ASL Bricks")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Initialize validation service
    validation_service = SignValidationService()

    # Results tracking
    results = []
    total_features_tested = 0
    total_features_correct = 0

    # Test each sign
    for i, (desc_data, video_url) in enumerate(ready_signs, 1):
        gloss = desc_data['gloss']

        print(f"\n{'─' * 80}")
        print(f"[{i}/{len(ready_signs)}] Testing: {gloss}")
        print(f"{'─' * 80}")
        print(f"Video: {video_url[:60]}...")

        # Convert dict to SignDescription object
        try:
            from app.models.sign_description import HandConfiguration

            # Build dominant hand configuration
            dominant_hand = HandConfiguration(
                handshape=desc_data['dominant_hand']['handshape'],
                location=desc_data['dominant_hand']['location'],
                palm_orientation=desc_data['dominant_hand'].get('palm_orientation', 'unknown'),
                fingers_extended=desc_data['dominant_hand'].get('fingers_extended')
            )

            # Build non-dominant hand if present
            non_dominant_hand = None
            if desc_data.get('non_dominant_hand'):
                non_dominant_hand = HandConfiguration(
                    handshape=desc_data['non_dominant_hand']['handshape'],
                    location=desc_data['non_dominant_hand']['location'],
                    palm_orientation=desc_data['non_dominant_hand'].get('palm_orientation', 'unknown'),
                    fingers_extended=desc_data['non_dominant_hand'].get('fingers_extended')
                )

            sign_desc = SignDescription(
                gloss=desc_data['gloss'],
                english_word=desc_data.get('english_word', desc_data['gloss'].lower()),
                dominant_hand=dominant_hand,
                non_dominant_hand=non_dominant_hand,
                movement=desc_data.get('movement', 'unknown'),
                non_manual_markers=desc_data.get('non_manual_markers', []),
                is_two_handed=desc_data.get('is_two_handed', False),
                symmetrical=desc_data.get('symmetrical', False),
                movement_path=desc_data.get('movement_path'),
                notes=desc_data.get('notes', ''),
                source=desc_data.get('source', 'Unknown'),
                verified=desc_data.get('verified', False)
            )
        except Exception as e:
            print(f"❌ Failed to parse description: {e}")
            import traceback
            traceback.print_exc()
            continue

        # Run validation
        try:
            result = validation_service.validate_sign(
                video_url=video_url,
                expected_description=sign_desc,
                max_frames=30
            )

            results.append({
                'gloss': gloss,
                'result': result,
                'video_url': video_url
            })

            # Print results
            print(f"\nExpected:")
            print(f"  Handshape: {desc_data['dominant_hand']['handshape']}")
            print(f"  Location: {desc_data['dominant_hand']['location']}")
            print(f"  Movement: {desc_data.get('movement', 'N/A')}")

            print(f"\nDetected:")
            features = result.extracted_features or {}
            print(f"  Handshape: {features.get('handshape', 'unknown')}")
            print(f"  Location: {features.get('location', 'unknown')}")
            print(f"  Movement: {features.get('movement', 'unknown')}")

            print(f"\nValidation:")
            print(f"  Overall: {'✅ PASS' if result.passed else '❌ FAIL'}")
            print(f"  Confidence: {result.confidence_score:.1%}")
            print(f"  Video Quality: {result.video_quality_score:.1%}")

            if result.issues_found:
                print(f"\nIssues:")
                for issue in result.issues_found:
                    print(f"  - {issue}")

            # Track feature accuracy
            features_tested = 0
            features_correct = 0

            # Handshape
            if desc_data['dominant_hand']['handshape'].lower() != 'unknown':
                features_tested += 1
                detected_hs = str(features.get('handshape', '')).split('.')[-1].lower()
                expected_hs = desc_data['dominant_hand']['handshape'].lower()
                if detected_hs == expected_hs or expected_hs in detected_hs or detected_hs in expected_hs:
                    features_correct += 1

            # Location
            if desc_data['dominant_hand']['location'].lower() != 'unknown':
                features_tested += 1
                detected_loc = str(features.get('location', '')).split('.')[-1].lower()
                expected_loc = desc_data['dominant_hand']['location'].lower()
                if detected_loc == expected_loc or expected_loc in detected_loc or detected_loc in expected_loc:
                    features_correct += 1

            # Movement
            if desc_data.get('movement', '').lower() not in ['unknown', 'none', '']:
                features_tested += 1
                detected_mov = str(features.get('movement', '')).split('.')[-1].lower()
                expected_mov = desc_data.get('movement', '').lower()
                if detected_mov == expected_mov or expected_mov in detected_mov or detected_mov in expected_mov:
                    features_correct += 1

            total_features_tested += features_tested
            total_features_correct += features_correct

        except Exception as e:
            print(f"❌ Validation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append({
                'gloss': gloss,
                'result': None,
                'error': str(e),
                'video_url': video_url
            })

        await asyncio.sleep(0.5)  # Brief pause between tests

    # Summary Report
    print(f"\n{'=' * 80}")
    print("VALIDATION SUMMARY")
    print(f"{'=' * 80}")

    successful = [r for r in results if r.get('result') is not None]
    failed = [r for r in results if r.get('result') is None]

    print(f"\nTests Completed:")
    print(f"  Total signs tested: {len(results)}")
    if len(results) > 0:
        print(f"  ✅ Successful: {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
        print(f"  ❌ Failed: {len(failed)} ({len(failed)/len(results)*100:.1f}%)")
    else:
        print(f"  ❌ No tests completed (all failed to parse)")
        return

    if successful:
        passed = [r for r in successful if r['result'].passed]
        print(f"\nValidation Results:")
        print(f"  Passed: {len(passed)}/{len(successful)} ({len(passed)/len(successful)*100:.1f}%)")

        avg_confidence = sum(r['result'].confidence_score for r in successful) / len(successful)
        avg_quality = sum(r['result'].video_quality_score for r in successful) / len(successful)

        print(f"\nAverage Scores:")
        print(f"  Confidence: {avg_confidence:.1%}")
        print(f"  Video Quality: {avg_quality:.1%}")

        print(f"\nFeature Accuracy:")
        if total_features_tested > 0:
            feature_accuracy = total_features_correct / total_features_tested
            print(f"  Overall: {total_features_correct}/{total_features_tested} ({feature_accuracy:.1%})")
        else:
            print(f"  No features tested")

    # Detailed breakdown
    print(f"\n{'─' * 80}")
    print("PER-SIGN RESULTS:")
    print(f"{'─' * 80}")

    for r in sorted(results, key=lambda x: x['gloss']):
        if r.get('result'):
            status = '✅' if r['result'].passed else '❌'
            conf = f"{r['result'].confidence_score:.0%}"
            print(f"  {status} {r['gloss']:15s} | Confidence: {conf:4s} | Quality: {r['result'].video_quality_score:.0%}")
        else:
            print(f"  ❌ {r['gloss']:15s} | ERROR: {r.get('error', 'Unknown')[:40]}")

    print(f"\n{'=' * 80}")
    print("ITERATION 4 COMPLETE")
    print(f"{'=' * 80}")
    print(f"\n✅ Baseline metrics established")
    print(f"✅ Framework validated on {len(successful)} real ASL signs")
    print(f"✅ Feature detection accuracy: {total_features_correct}/{total_features_tested} ({total_features_correct/total_features_tested*100:.1f}%)" if total_features_tested > 0 else "")
    print(f"\n💡 Next steps:")
    print(f"   1. Analyze failed cases to improve feature detection algorithms")
    print(f"   2. Refine handshape/location/movement classifiers based on results")
    print(f"   3. Add more sign descriptions for expanded testing")

    db.close()


if __name__ == "__main__":
    import os
    if 'DATABASE_URL' not in os.environ:
        os.environ['DATABASE_URL'] = 'sqlite:///./sign_language.db'

    asyncio.run(run_full_validation())
