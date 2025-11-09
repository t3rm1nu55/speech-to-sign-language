#!/usr/bin/env python3
"""
Analyze avatar accuracy across all 70 signs

Identifies:
- Average accuracy across dataset
- Best performing signs
- Worst performing signs
- Bottleneck areas (body vs hands)
"""

import sys
import json
from pathlib import Path
from avatar_accuracy_scorer import AvatarAccuracyScorer


def main():
    """Analyze accuracy for all signs"""

    data_dir = Path("/home/user/speech-to-sign-language/avatar_training_data")
    scorer = AvatarAccuracyScorer()

    sign_dirs = sorted([
        d for d in data_dir.iterdir()
        if d.is_dir() and (d / 'pose_descriptions.json').exists()
    ])

    print(f"\n{'='*100}")
    print(f"ANALYZING AVATAR ACCURACY ACROSS ALL SIGNS")
    print(f"{'='*100}\n")
    print(f"Total signs to analyze: {len(sign_dirs)}")
    print(f"Target accuracy: 99%+\n")

    results = []

    for i, sign_dir in enumerate(sign_dirs, 1):
        print(f"[{i}/{len(sign_dirs)}] Analyzing {sign_dir.name.upper()}...", end=' ')

        try:
            report = scorer.generate_accuracy_report(sign_dir)

            result = {
                'sign': sign_dir.name.upper(),
                'overall': report['avg_overall_accuracy'],
                'body': report['avg_body_accuracy'],
                'right_hand': report['avg_right_hand_accuracy'],
                'left_hand': report['avg_left_hand_accuracy'],
                'meets_target': report['meets_99_target']
            }
            results.append(result)

            status = '✅' if result['meets_target'] else '❌'
            print(f"{result['overall']:.2f}% {status}")

        except Exception as e:
            print(f"ERROR: {e}")
            continue

    # Sort by overall accuracy
    results.sort(key=lambda x: x['overall'], reverse=True)

    # Calculate statistics
    avg_overall = sum(r['overall'] for r in results) / len(results)
    avg_body = sum(r['body'] for r in results if r['body'] > 0) / len([r for r in results if r['body'] > 0])
    avg_right = sum(r['right_hand'] for r in results if r['right_hand'] > 0) / len([r for r in results if r['right_hand'] > 0])
    avg_left = sum(r['left_hand'] for r in results if r['left_hand'] > 0 and not (r['left_hand'] != r['left_hand'])) / len([r for r in results if r['left_hand'] > 0 and not (r['left_hand'] != r['left_hand'])])

    meeting_target = sum(1 for r in results if r['meets_target'])

    print(f"\n{'='*100}")
    print(f"ACCURACY ANALYSIS SUMMARY")
    print(f"{'='*100}\n")

    print(f"Average Accuracy:")
    print(f"  Overall:     {avg_overall:>6.2f}%")
    print(f"  Body:        {avg_body:>6.2f}%")
    print(f"  Right Hand:  {avg_right:>6.2f}%")
    print(f"  Left Hand:   {avg_left:>6.2f}%")
    print(f"\nTarget Achievement:")
    print(f"  Signs meeting 99% target: {meeting_target}/{len(results)} ({100*meeting_target/len(results):.1f}%)")
    print(f"  Signs below 99% target:   {len(results)-meeting_target}/{len(results)} ({100*(len(results)-meeting_target)/len(results):.1f}%)")

    # Top 10 performers
    print(f"\n{'='*100}")
    print(f"TOP 10 PERFORMERS")
    print(f"{'='*100}\n")
    print(f"{'Rank':<6} {'Sign':<15} {'Overall':<10} {'Body':<10} {'R-Hand':<10} {'L-Hand':<10}")
    print(f"{'-'*80}")

    for i, r in enumerate(results[:10], 1):
        print(f"{i:<6} {r['sign']:<15} {r['overall']:>6.2f}%   {r['body']:>6.2f}%   {r['right_hand']:>6.2f}%   {r['left_hand']:>6.2f}%")

    # Bottom 10 performers
    print(f"\n{'='*100}")
    print(f"BOTTOM 10 PERFORMERS (Need Most Improvement)")
    print(f"{'='*100}\n")
    print(f"{'Rank':<6} {'Sign':<15} {'Overall':<10} {'Body':<10} {'R-Hand':<10} {'L-Hand':<10}")
    print(f"{'-'*80}")

    for i, r in enumerate(results[-10:], 1):
        print(f"{i:<6} {r['sign']:<15} {r['overall']:>6.2f}%   {r['body']:>6.2f}%   {r['right_hand']:>6.2f}%   {r['left_hand']:>6.2f}%")

    # Identify bottlenecks
    print(f"\n{'='*100}")
    print(f"BOTTLENECK ANALYSIS")
    print(f"{'='*100}\n")

    body_issues = [r for r in results if r['body'] < 95]
    right_hand_issues = [r for r in results if r['right_hand'] < 85]
    left_hand_issues = [r for r in results if r['left_hand'] < 85 and not (r['left_hand'] != r['left_hand'])]

    print(f"Signs with body accuracy < 95%:       {len(body_issues)}")
    print(f"Signs with right hand accuracy < 85%: {len(right_hand_issues)}")
    print(f"Signs with left hand accuracy < 85%:  {len(left_hand_issues)}")

    print(f"\nPrimary bottleneck: ", end='')
    if len(right_hand_issues) >= len(left_hand_issues) and len(right_hand_issues) >= len(body_issues):
        print(f"Right Hand ({len(right_hand_issues)} signs)")
    elif len(left_hand_issues) >= len(body_issues):
        print(f"Left Hand ({len(left_hand_issues)} signs)")
    else:
        print(f"Body ({len(body_issues)} signs)")

    # Save full report
    output_dir = Path("/home/user/speech-to-sign-language/avatar_final_output")
    output_dir.mkdir(exist_ok=True)

    report_data = {
        'summary': {
            'avg_overall': avg_overall,
            'avg_body': avg_body,
            'avg_right_hand': avg_right,
            'avg_left_hand': avg_left,
            'meeting_target': meeting_target,
            'total_signs': len(results)
        },
        'all_results': results
    }

    output_file = output_dir / "accuracy_analysis_report.json"
    with open(output_file, 'w') as f:
        json.dump(report_data, f, indent=2)

    print(f"\n📁 Full report saved to: {output_file}\n")


if __name__ == "__main__":
    main()
