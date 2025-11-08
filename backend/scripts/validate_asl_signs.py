"""
Comprehensive ASL Sign Validation Script
Validates MediaPipe interpretations against ASL linguistic descriptions
Performs iterative refinement of descriptive framework
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import json
from datetime import datetime
from typing import List, Dict
from app.database import SessionLocal
from app.models.sign_dictionary import SignEntry
from app.models.sign_description import (
    SignDescription, ValidationReport, SignValidationResult,
    Handshape, Location, Movement, PalmOrientation, HandConfiguration
)
from app.services.sign_validation import SignValidationService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SignValidationRunner:
    """
    Runs comprehensive validation tests on ASL signs
    """

    def __init__(self):
        self.db = SessionLocal()
        self.validation_service = SignValidationService()
        self.sign_descriptions: Dict[str, SignDescription] = {}
        self.iteration = 1

    def load_sign_descriptions(self, json_path: str):
        """Load sign descriptions from JSON file"""
        logger.info(f"Loading sign descriptions from {json_path}")

        with open(json_path, 'r') as f:
            data = json.load(f)

        signs = data.get('signs', [])
        logger.info(f"Found {len(signs)} sign descriptions")

        for sign_data in signs:
            try:
                # Parse handshape enums
                dom_hand = sign_data['dominant_hand']
                dom_hand['handshape'] = Handshape(dom_hand['handshape'])
                dom_hand['location'] = Location(dom_hand['location'])
                dom_hand['palm_orientation'] = PalmOrientation(dom_hand['palm_orientation'])

                dominant_config = HandConfiguration(**dom_hand)

                # Parse non-dominant hand if present
                non_dom_config = None
                if sign_data.get('non_dominant_hand'):
                    non_dom = sign_data['non_dominant_hand']
                    non_dom['handshape'] = Handshape(non_dom['handshape'])
                    non_dom['location'] = Location(non_dom['location'])
                    non_dom['palm_orientation'] = PalmOrientation(non_dom['palm_orientation'])
                    non_dom_config = HandConfiguration(**non_dom)

                # Parse movement enum
                movement = Movement(sign_data['movement'])

                # Create SignDescription
                description = SignDescription(
                    gloss=sign_data['gloss'],
                    english_word=sign_data['english_word'],
                    dominant_hand=dominant_config,
                    non_dominant_hand=non_dom_config,
                    movement=movement,
                    is_two_handed=sign_data.get('is_two_handed', False),
                    symmetrical=sign_data.get('symmetrical', False),
                    movement_path=sign_data.get('movement_path'),
                    contact_location=Location(sign_data['contact_location']) if sign_data.get('contact_location') else None,
                    notes=sign_data.get('notes'),
                    source=sign_data.get('source'),
                    verified=sign_data.get('verified', False)
                )

                self.sign_descriptions[sign_data['gloss']] = description

            except Exception as e:
                logger.error(f"Error parsing {sign_data.get('gloss', 'unknown')}: {e}")

        logger.info(f"Loaded {len(self.sign_descriptions)} valid sign descriptions")

    def get_video_url_for_sign(self, gloss: str) -> str:
        """Get video URL from database for a sign"""
        # Query database for sign
        sign_entry = self.db.query(SignEntry).filter(
            SignEntry.gloss == gloss.upper(),
            SignEntry.video_url.isnot(None)
        ).first()

        if sign_entry:
            return sign_entry.video_url

        # Try alternative query with word match
        sign_entry = self.db.query(SignEntry).filter(
            SignEntry.word == gloss.lower(),
            SignEntry.video_url.isnot(None)
        ).first()

        if sign_entry:
            return sign_entry.video_url

        return None

    async def validate_single_sign(self, gloss: str) -> SignValidationResult:
        """Validate a single sign"""
        logger.info(f"\n{'='*80}")
        logger.info(f"VALIDATING: {gloss}")
        logger.info(f"{'='*80}")

        description = self.sign_descriptions.get(gloss)
        if not description:
            logger.error(f"No description found for {gloss}")
            return None

        # Get video URL
        video_url = self.get_video_url_for_sign(gloss)
        if not video_url:
            logger.warning(f"No video URL found for {gloss}")
            result = SignValidationResult(
                gloss=gloss,
                video_url="N/A",
                passed=False,
                confidence_score=0.0,
                expected_description=description
            )
            result.issues_found.append("No video available in database")
            return result

        logger.info(f"Video URL: {video_url}")

        # Perform validation
        result = self.validation_service.validate_sign(
            video_url=video_url,
            expected_description=description,
            max_frames=30
        )

        # Print detailed results
        self._print_validation_result(result)

        return result

    def _print_validation_result(self, result: SignValidationResult):
        """Print detailed validation results"""
        print(f"\n{'─'*80}")
        print(f"VALIDATION RESULT: {result.gloss}")
        print(f"{'─'*80}")

        # Overall status
        status_icon = "✅" if result.passed else "❌"
        print(f"\n{status_icon} Overall: {'PASSED' if result.passed else 'FAILED'}")
        print(f"   Confidence Score: {result.confidence_score*100:.1f}%")

        # Video quality
        if result.video_quality_score:
            quality_icon = "✅" if result.video_quality_score > 0.7 else "⚠️" if result.video_quality_score > 0.5 else "❌"
            print(f"\n{quality_icon} Video Quality: {result.video_quality_score*100:.1f}%")

        if result.pose_detection_rate:
            detect_icon = "✅" if result.pose_detection_rate > 0.8 else "⚠️"
            print(f"{detect_icon} Pose Detection: {result.pose_detection_rate*100:.1f}%")

        print(f"   Frames Analyzed: {result.frame_count}")

        # Feature validation
        print(f"\n📊 Feature Validation:")

        if result.handshape_confidence is not None:
            hs_icon = "✅" if result.handshape_match else "❌"
            print(f"   {hs_icon} Handshape: {result.handshape_confidence*100:.1f}%")

        if result.location_confidence is not None:
            loc_icon = "✅" if result.location_match else "❌"
            print(f"   {loc_icon} Location: {result.location_confidence*100:.1f}%")

        if result.movement_confidence is not None:
            mov_icon = "✅" if result.movement_match else "❌"
            print(f"   {mov_icon} Movement: {result.movement_confidence*100:.1f}%")

        if result.palm_orientation_confidence is not None:
            palm_icon = "✅" if result.palm_orientation_match else "❌"
            print(f"   {palm_icon} Palm Orientation: {result.palm_orientation_confidence*100:.1f}%")

        # Expected vs Actual
        if result.expected_description and result.extracted_features:
            print(f"\n🔍 Expected vs Detected:")
            exp = result.expected_description

            print(f"   Handshape:")
            print(f"      Expected: {exp.dominant_hand.handshape.value}")
            print(f"      Detected: {result.extracted_features.get('handshape', 'unknown')}")

            print(f"   Location:")
            print(f"      Expected: {exp.dominant_hand.location.value}")
            print(f"      Detected: {result.extracted_features.get('location', 'unknown')}")

            print(f"   Movement:")
            print(f"      Expected: {exp.movement.value}")
            print(f"      Detected: {result.extracted_features.get('movement', 'unknown')}")

            if result.extracted_features.get('hand_velocity') is not None:
                print(f"   Hand Velocity: {result.extracted_features['hand_velocity']:.4f}")

        # Issues found
        if result.issues_found:
            print(f"\n⚠️  Issues Found ({len(result.issues_found)}):")
            for issue in result.issues_found:
                print(f"   • {issue}")

        # Suggestions
        if result.suggestions:
            print(f"\n💡 Suggestions ({len(result.suggestions)}):")
            for suggestion in result.suggestions:
                print(f"   • {suggestion}")

        print(f"\n{'─'*80}\n")

    async def run_validation_suite(
        self,
        signs_to_test: List[str] = None,
        max_signs: int = None
    ) -> ValidationReport:
        """
        Run complete validation suite

        Args:
            signs_to_test: Specific signs to test (None = all)
            max_signs: Maximum number of signs to test

        Returns:
            Comprehensive validation report
        """
        print(f"\n{'='*80}")
        print(f"ASL SIGN VALIDATION SUITE - ITERATION {self.iteration}")
        print(f"{'='*80}")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Descriptions Loaded: {len(self.sign_descriptions)}")

        # Determine which signs to test
        if signs_to_test:
            test_glosses = signs_to_test
        else:
            test_glosses = list(self.sign_descriptions.keys())

        if max_signs:
            test_glosses = test_glosses[:max_signs]

        print(f"Signs to Test: {len(test_glosses)}")
        print(f"{'='*80}\n")

        # Run validations
        results: List[SignValidationResult] = []

        for gloss in test_glosses:
            result = await self.validate_single_sign(gloss)
            if result:
                results.append(result)

            # Small delay to avoid overwhelming video servers
            await asyncio.sleep(1)

        # Generate comprehensive report
        report = self._generate_report(results)

        # Print summary
        self._print_summary(report)

        # Save report
        self._save_report(report)

        return report

    def _generate_report(self, results: List[SignValidationResult]) -> ValidationReport:
        """Generate comprehensive validation report"""

        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count

        # Calculate average confidence
        confidences = [r.confidence_score for r in results if r.confidence_score > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Feature accuracies
        handshape_matches = [r for r in results if r.handshape_match is not None]
        handshape_accuracy = (
            sum(1 for r in handshape_matches if r.handshape_match) / len(handshape_matches)
            if handshape_matches else 0.0
        )

        location_matches = [r for r in results if r.location_match is not None]
        location_accuracy = (
            sum(1 for r in location_matches if r.location_match) / len(location_matches)
            if location_matches else 0.0
        )

        movement_matches = [r for r in results if r.movement_match is not None]
        movement_accuracy = (
            sum(1 for r in movement_matches if r.movement_match) / len(movement_matches)
            if movement_matches else 0.0
        )

        palm_matches = [r for r in results if r.palm_orientation_match is not None]
        palm_accuracy = (
            sum(1 for r in palm_matches if r.palm_orientation_match) / len(palm_matches)
            if palm_matches else 0.0
        )

        # Identify framework issues
        framework_issues = []

        # Check for consistent failures
        if handshape_accuracy < 0.5:
            framework_issues.append(
                "Handshape detection accuracy is low (<50%). "
                "May need refined handshape classification algorithm or better hand landmark tracking."
            )

        if location_accuracy < 0.5:
            framework_issues.append(
                "Location detection accuracy is low (<50%). "
                "Location zones may need adjustment or more granular definitions."
            )

        if movement_accuracy < 0.5:
            framework_issues.append(
                "Movement detection accuracy is low (<50%). "
                "Movement classification may need more sophisticated trajectory analysis."
            )

        # Check for video quality issues
        poor_quality_videos = [
            r for r in results
            if r.video_quality_score and r.video_quality_score < 0.6
        ]
        if len(poor_quality_videos) > len(results) * 0.3:
            framework_issues.append(
                f"{len(poor_quality_videos)} videos have poor quality (<60%). "
                "Consider finding alternative video sources or improving pose extraction."
            )

        # Generate recommendations
        recommendations = []

        if avg_confidence < 0.7:
            recommendations.append(
                "Overall confidence is below 70%. Focus on improving feature detection algorithms."
            )

        if handshape_accuracy < location_accuracy:
            recommendations.append(
                "Handshape detection is weaker than location detection. "
                "Prioritize improving hand landmark analysis and finger extension detection."
            )

        if movement_accuracy > 0.8:
            recommendations.append(
                "Movement detection is performing well (>80%). "
                "This can serve as a reliable anchor for sign identification."
            )

        # Add specific recommendations based on common issues
        all_issues = []
        for result in results:
            all_issues.extend(result.issues_found)

        if all_issues.count("Handshape mismatch") > len(results) * 0.3:
            recommendations.append(
                "Handshape mismatches are common. Consider implementing ML-based handshape classifier."
            )

        report = ValidationReport(
            total_signs_tested=len(results),
            passed_count=passed_count,
            failed_count=failed_count,
            average_confidence=avg_confidence,
            handshape_accuracy=handshape_accuracy,
            location_accuracy=location_accuracy,
            movement_accuracy=movement_accuracy,
            palm_accuracy=palm_accuracy,
            sign_results=results,
            framework_issues=framework_issues,
            recommendations=recommendations,
            iteration_number=self.iteration,
            date_tested=datetime.now().isoformat()
        )

        return report

    def _print_summary(self, report: ValidationReport):
        """Print validation summary"""
        print(f"\n{'='*80}")
        print(f"VALIDATION SUMMARY - ITERATION {report.iteration_number}")
        print(f"{'='*80}")

        print(f"\n📊 Overall Results:")
        print(f"   Total Signs Tested: {report.total_signs_tested}")
        print(f"   ✅ Passed: {report.passed_count} ({report.passed_count/report.total_signs_tested*100:.1f}%)")
        print(f"   ❌ Failed: {report.failed_count} ({report.failed_count/report.total_signs_tested*100:.1f}%)")
        print(f"   Average Confidence: {report.average_confidence*100:.1f}%")

        print(f"\n🎯 Feature Accuracy:")
        print(f"   Handshape: {report.handshape_accuracy*100:.1f}%")
        print(f"   Location: {report.location_accuracy*100:.1f}%")
        print(f"   Movement: {report.movement_accuracy*100:.1f}%")
        print(f"   Palm Orientation: {report.palm_accuracy*100:.1f}%")

        if report.framework_issues:
            print(f"\n⚠️  Framework Issues ({len(report.framework_issues)}):")
            for i, issue in enumerate(report.framework_issues, 1):
                print(f"   {i}. {issue}")

        if report.recommendations:
            print(f"\n💡 Recommendations ({len(report.recommendations)}):")
            for i, rec in enumerate(report.recommendations, 1):
                print(f"   {i}. {rec}")

        # Top performers
        top_signs = sorted(
            report.sign_results,
            key=lambda r: r.confidence_score,
            reverse=True
        )[:5]

        print(f"\n🏆 Top 5 Performers:")
        for i, result in enumerate(top_signs, 1):
            status = "✅" if result.passed else "❌"
            print(f"   {i}. {result.gloss}: {result.confidence_score*100:.1f}% {status}")

        # Bottom performers
        bottom_signs = sorted(
            report.sign_results,
            key=lambda r: r.confidence_score
        )[:5]

        print(f"\n⚠️  Bottom 5 Performers:")
        for i, result in enumerate(bottom_signs, 1):
            print(f"   {i}. {result.gloss}: {result.confidence_score*100:.1f}%")
            if result.issues_found:
                print(f"      Issues: {', '.join(result.issues_found[:2])}")

        print(f"\n{'='*80}\n")

    def _save_report(self, report: ValidationReport):
        """Save validation report to file"""
        output_dir = Path(__file__).parent.parent / "validation_reports"
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"validation_report_iter{report.iteration_number}_{timestamp}.json"
        filepath = output_dir / filename

        # Convert to dict for JSON serialization
        report_dict = report.dict()

        with open(filepath, 'w') as f:
            json.dump(report_dict, f, indent=2, default=str)

        logger.info(f"Report saved to: {filepath}")

    def cleanup(self):
        """Close database connection"""
        self.db.close()


async def main():
    """Main execution"""
    runner = SignValidationRunner()

    try:
        # Load sign descriptions
        descriptions_path = Path(__file__).parent.parent / "data" / "asl_sign_descriptions.json"
        runner.load_sign_descriptions(str(descriptions_path))

        # Run validation suite
        # Start with a smaller subset for initial testing
        priority_signs = [
            "HELLO", "HELP", "THANK-YOU", "YES", "NO",
            "PLEASE", "SORRY", "GOOD", "BAD",
            "WHAT", "WHERE", "WHO", "HOW",
            "I", "YOU", "NAME", "HAPPY", "SAD"
        ]

        print("\n🚀 Starting validation with priority signs...")
        report = await runner.run_validation_suite(
            signs_to_test=priority_signs,
            max_signs=None
        )

        print(f"\n✅ Validation complete!")
        print(f"   Iteration: {report.iteration_number}")
        print(f"   Success Rate: {report.passed_count/report.total_signs_tested*100:.1f}%")
        print(f"   Average Confidence: {report.average_confidence*100:.1f}%")

    finally:
        runner.cleanup()


if __name__ == "__main__":
    import os
    if 'DATABASE_URL' not in os.environ:
        os.environ['DATABASE_URL'] = 'sqlite:///./sign_language.db'

    asyncio.run(main())
