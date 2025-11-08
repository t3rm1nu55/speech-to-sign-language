#!/usr/bin/env python3
"""
Extract ALL ASL Bricks signs for comprehensive avatar training
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.sign_dictionary import SignEntry
from app.database import SessionLocal
from extract_and_describe_frames import FramePoseDescriber

def main():
    """Extract all ASL Bricks signs"""

    # Get all ASL Bricks videos from database
    db = SessionLocal()
    asl_bricks = db.query(SignEntry).filter(
        SignEntry.video_url.like('%aslbricks%')
    ).all()

    print(f"\n{'='*100}")
    print(f"EXTRACTING ALL ASL BRICKS SIGNS")
    print(f"{'='*100}\n")
    print(f"Total signs to extract: {len(asl_bricks)}\n")

    describer = FramePoseDescriber(output_dir="/home/user/speech-to-sign-language/avatar_training_data")

    success_count = 0
    fail_count = 0
    total_frames = 0

    for i, entry in enumerate(asl_bricks, 1):
        gloss = entry.word.upper()
        video_url = entry.video_url

        print(f"[{i}/{len(asl_bricks)}] Processing: {gloss}")

        try:
            sign_dir = describer.extract_all_frames(gloss, video_url)

            # Count frames
            import json
            desc_file = sign_dir / "pose_descriptions.json"
            with open(desc_file) as f:
                data = json.load(f)
                frame_count = data['total_frames']
                total_frames += frame_count

            print(f"  ✅ Success: {frame_count} frames\n")
            success_count += 1

        except Exception as e:
            print(f"  ❌ Failed: {e}\n")
            fail_count += 1
            continue

    print(f"\n{'='*100}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*100}\n")
    print(f"Successfully extracted: {success_count}/{len(asl_bricks)} signs")
    print(f"Failed: {fail_count}")
    print(f"Total frames extracted: {total_frames}")
    print(f"\nData saved to: /home/user/speech-to-sign-language/avatar_training_data/")
    print(f"\nReady for avatar training!\n")

if __name__ == "__main__":
    main()
