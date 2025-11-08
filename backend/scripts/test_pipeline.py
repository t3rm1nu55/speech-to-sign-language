#!/usr/bin/env python3
"""
Test the batch processing pipeline on a small subset of signs
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pathlib import Path
from batch_process_all_signs import BatchProcessor

def main():
    """Test pipeline on 3 signs"""

    data_dir = Path("/home/user/speech-to-sign-language/avatar_training_data")

    processor = BatchProcessor(data_dir)

    # Get first 3 signs with pose data
    sign_dirs = processor.find_all_signs()
    test_signs = sign_dirs[:3]

    print(f"\n{'#'*100}")
    print(f"# TESTING BATCH PROCESSING PIPELINE")
    print(f"# Testing {len(test_signs)} signs: {[s.name for s in test_signs]}")
    print(f"{'#'*100}\n")

    # Process test signs
    results = []
    for i, sign_dir in enumerate(test_signs, 1):
        print(f"\n[{i}/{len(test_signs)}] {sign_dir.name.upper()}")
        result = processor.process_sign(sign_dir)
        results.append(result)

    # Generate report
    processor._generate_final_report(results)

    print("\n" + "="*100)
    print("PIPELINE TEST COMPLETE")
    print("="*100)

if __name__ == "__main__":
    main()
