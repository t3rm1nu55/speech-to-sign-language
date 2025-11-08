#!/usr/bin/env python3
"""
Batch Processing Pipeline for All ASL Signs

Processes all extracted signs through the complete pipeline:
1. Frame extraction (already done)
2. Avatar rendering
3. Accuracy scoring
4. Animation export (all formats)
5. Generate final delivery package

Goal: Create production-ready avatar animation data for all 70 signs
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pathlib import Path
from avatar_renderer import AvatarRenderer
from avatar_accuracy_scorer import AvatarAccuracyScorer
from export_animation_data import AnimationExporter
import json
from typing import List, Dict
import time


class BatchProcessor:
    """Batch process all extracted signs"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.renderer = AvatarRenderer()
        self.scorer = AvatarAccuracyScorer()
        self.exporter = AnimationExporter()

        self.output_dir = Path("/home/user/speech-to-sign-language/avatar_final_output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def find_all_signs(self) -> List[Path]:
        """Find all extracted sign directories"""

        sign_dirs = []

        for item in self.data_dir.iterdir():
            if item.is_dir():
                # Check if it has pose data
                pose_file = item / "pose_descriptions.json"
                if pose_file.exists():
                    sign_dirs.append(item)

        return sorted(sign_dirs, key=lambda x: x.name)

    def process_sign(self, sign_dir: Path) -> Dict:
        """Process a single sign through complete pipeline"""

        sign_name = sign_dir.name.upper()
        print(f"\n{'='*100}")
        print(f"PROCESSING: {sign_name}")
        print(f"{'='*100}\n")

        start_time = time.time()

        result = {
            'sign': sign_name,
            'success': False,
            'steps_completed': [],
            'errors': [],
            'files_generated': [],
            'accuracy_score': 0.0,
            'processing_time': 0.0
        }

        try:
            # Step 1: Render avatar comparison images
            print("Step 1/3: Rendering avatar...")
            try:
                self.renderer.batch_render_sign(sign_dir, sample_every=10)
                result['steps_completed'].append('rendering')
                result['files_generated'].extend([
                    str(sign_dir / "avatar_renders")
                ])
            except Exception as e:
                result['errors'].append(f"Rendering failed: {e}")
                print(f"  ❌ Error: {e}")

            # Step 2: Score accuracy
            print("\nStep 2/3: Scoring accuracy...")
            try:
                accuracy_report = self.scorer.generate_accuracy_report(sign_dir)
                result['accuracy_score'] = accuracy_report['avg_overall_accuracy']
                result['steps_completed'].append('scoring')

                # Save accuracy report
                report_file = sign_dir / "accuracy_report.json"
                with open(report_file, 'w') as f:
                    json.dump(accuracy_report, f, indent=2)
                result['files_generated'].append(str(report_file))

            except Exception as e:
                result['errors'].append(f"Scoring failed: {e}")
                print(f"  ❌ Error: {e}")

            # Step 3: Export animations
            print("\nStep 3/3: Exporting animations...")
            try:
                self.exporter.export_all_formats(sign_dir)
                result['steps_completed'].append('export')
                result['files_generated'].extend([
                    str(sign_dir / "animation_exports")
                ])
            except Exception as e:
                result['errors'].append(f"Export failed: {e}")
                print(f"  ❌ Error: {e}")

            # Mark as success if all steps completed
            if len(result['steps_completed']) == 3:
                result['success'] = True

        except Exception as e:
            result['errors'].append(f"Critical error: {e}")
            print(f"\n❌ Critical error: {e}")

        result['processing_time'] = time.time() - start_time

        # Print summary
        print(f"\n{'-'*100}")
        if result['success']:
            print(f"✅ {sign_name}: COMPLETE ({result['processing_time']:.1f}s)")
            print(f"   Accuracy: {result['accuracy_score']:.1f}%")
        else:
            print(f"❌ {sign_name}: FAILED ({result['processing_time']:.1f}s)")
            print(f"   Errors: {len(result['errors'])}")
        print(f"{'-'*100}\n")

        return result

    def process_all(self):
        """Process all extracted signs"""

        print(f"\n{'#'*100}")
        print(f"# BATCH PROCESSING ALL ASL SIGNS")
        print(f"# Data directory: {self.data_dir}")
        print(f"# Output directory: {self.output_dir}")
        print(f"{'#'*100}\n")

        # Find all signs
        sign_dirs = self.find_all_signs()
        print(f"Found {len(sign_dirs)} extracted signs\n")

        if not sign_dirs:
            print("❌ No extracted signs found!")
            return

        # Process each sign
        results = []
        for i, sign_dir in enumerate(sign_dirs, 1):
            print(f"\n[{i}/{len(sign_dirs)}] {sign_dir.name.upper()}")
            result = self.process_sign(sign_dir)
            results.append(result)

        # Generate final report
        self._generate_final_report(results)

        return results

    def _generate_final_report(self, results: List[Dict]):
        """Generate comprehensive final report"""

        print(f"\n{'#'*100}")
        print(f"# FINAL REPORT")
        print(f"{'#'*100}\n")

        total = len(results)
        successful = sum(1 for r in results if r['success'])
        failed = total - successful

        total_time = sum(r['processing_time'] for r in results)
        avg_time = total_time / total if total > 0 else 0

        avg_accuracy = sum(r['accuracy_score'] for r in results if r['accuracy_score'] > 0) / total if total > 0 else 0

        signs_meeting_99 = sum(1 for r in results if r['accuracy_score'] >= 99.0)

        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'summary': {
                'total_signs': total,
                'successful': successful,
                'failed': failed,
                'success_rate': (successful / total * 100) if total > 0 else 0,
                'total_processing_time': total_time,
                'avg_processing_time': avg_time,
                'avg_accuracy': avg_accuracy,
                'signs_meeting_99_target': signs_meeting_99
            },
            'results': results
        }

        # Save report
        report_file = self.output_dir / "batch_processing_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        # Print summary
        print(f"Total Signs Processed: {total}")
        print(f"  ✅ Successful: {successful} ({successful/total*100:.1f}%)")
        print(f"  ❌ Failed: {failed}")
        print()
        print(f"Performance:")
        print(f"  Total time: {total_time/60:.1f} minutes")
        print(f"  Avg per sign: {avg_time:.1f} seconds")
        print()
        print(f"Accuracy:")
        print(f"  Average accuracy: {avg_accuracy:.1f}%")
        print(f"  Signs meeting 99% target: {signs_meeting_99}/{total}")
        print()
        print(f"📁 Final report saved to: {report_file}")
        print()

        # List failed signs
        if failed > 0:
            print("Failed signs:")
            for r in results:
                if not r['success']:
                    print(f"  ❌ {r['sign']}: {', '.join(r['errors'])}")
            print()


def main():
    """Run batch processing"""

    # Check for data directory
    data_dir = Path("/home/user/speech-to-sign-language/avatar_training_data")

    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        print("Run extract_all_signs.py first to extract frames from videos")
        return

    processor = BatchProcessor(data_dir)
    processor.process_all()


if __name__ == "__main__":
    main()
