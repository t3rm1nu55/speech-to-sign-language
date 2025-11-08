"""
Comprehensive test runner with reporting
Downloads test data and runs all tests, generating detailed reports
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class TestRunner:
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "stages": {}
        }

    def run_command(self, command, description):
        """Run a shell command and capture output"""
        logger.info(f"\n{'='*70}")
        logger.info(f"{description}")
        logger.info(f"{'='*70}")

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self.test_dir.parent)
            )

            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Error running command: {str(e)}")
            return False

    def download_test_data(self):
        """Download test audio data"""
        logger.info("\n" + "="*70)
        logger.info("STAGE 1: Downloading Test Data")
        logger.info("="*70)

        success = self.run_command(
            "python tests/download_test_data.py",
            "Downloading speech datasets"
        )

        self.results["stages"]["data_download"] = {
            "success": success,
            "description": "Download real speech datasets"
        }

        return success

    def run_unit_tests(self):
        """Run unit tests"""
        logger.info("\n" + "="*70)
        logger.info("STAGE 2: Running Unit Tests")
        logger.info("="*70)

        # Run pytest with verbose output and generate JSON report
        success = self.run_command(
            "pytest tests/test_api_health.py tests/test_api_translation.py tests/test_services_translation.py -v --tb=short",
            "Running unit tests"
        )

        self.results["stages"]["unit_tests"] = {
            "success": success,
            "description": "API and service unit tests"
        }

        return success

    def run_speech_recognition_tests(self):
        """Run speech recognition tests with real audio"""
        logger.info("\n" + "="*70)
        logger.info("STAGE 3: Testing Speech Recognition")
        logger.info("="*70)

        success = self.run_command(
            "pytest tests/test_speech_with_real_audio.py -v -s --tb=short",
            "Testing speech recognition with real audio"
        )

        self.results["stages"]["speech_recognition"] = {
            "success": success,
            "description": "Speech recognition accuracy tests"
        }

        # Load results if available
        results_file = self.test_dir / "test_data" / "speech_recognition_results.json"
        if results_file.exists():
            with open(results_file, "r") as f:
                speech_results = json.load(f)
                self.results["stages"]["speech_recognition"]["metrics"] = {
                    "average_wer": speech_results.get("average_wer"),
                    "num_samples": speech_results.get("num_samples")
                }

        return success

    def run_integration_tests(self):
        """Run integration tests"""
        logger.info("\n" + "="*70)
        logger.info("STAGE 4: Testing Complete Pipeline")
        logger.info("="*70)

        success = self.run_command(
            "pytest tests/test_integration_pipeline.py -v -s --tb=short",
            "Testing complete speech-to-sign pipeline"
        )

        self.results["stages"]["integration"] = {
            "success": success,
            "description": "End-to-end pipeline integration tests"
        }

        # Load pipeline results if available
        results_file = self.test_dir / "test_data" / "pipeline_integration_results.json"
        if results_file.exists():
            with open(results_file, "r") as f:
                pipeline_results = json.load(f)
                self.results["stages"]["integration"]["metrics"] = {
                    "total_processing_time_ms": pipeline_results.get("total_processing_time_ms")
                }

        return success

    def generate_report(self):
        """Generate final test report"""
        logger.info("\n" + "="*70)
        logger.info("TEST SUMMARY")
        logger.info("="*70)

        all_passed = True
        for stage_name, stage_data in self.results["stages"].items():
            status = "✓ PASS" if stage_data["success"] else "✗ FAIL"
            logger.info(f"{stage_name:30} {status}")

            if "metrics" in stage_data:
                for metric, value in stage_data["metrics"].items():
                    logger.info(f"  {metric}: {value}")

            all_passed = all_passed and stage_data["success"]

        self.results["overall_success"] = all_passed

        # Save results
        report_file = self.test_dir / "test_data" / "comprehensive_test_report.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)

        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"\nDetailed report saved to: {report_file}")

        # Generate markdown report
        self.generate_markdown_report()

        return all_passed

    def generate_markdown_report(self):
        """Generate markdown test report"""
        report_lines = [
            "# Speech-to-Sign Language Backend Test Report",
            f"\n**Generated:** {self.results['timestamp']}",
            f"\n**Overall Result:** {'✓ PASSED' if self.results.get('overall_success') else '✗ FAILED'}",
            "\n## Test Stages\n"
        ]

        for stage_name, stage_data in self.results["stages"].items():
            status_icon = "✓" if stage_data["success"] else "✗"
            report_lines.append(f"### {status_icon} {stage_name.replace('_', ' ').title()}")
            report_lines.append(f"\n{stage_data['description']}\n")

            if "metrics" in stage_data:
                report_lines.append("**Metrics:**")
                for metric, value in stage_data["metrics"].items():
                    report_lines.append(f"- {metric}: {value}")
                report_lines.append("")

        markdown_file = self.test_dir / "test_data" / "TEST_REPORT.md"
        with open(markdown_file, "w") as f:
            f.write("\n".join(report_lines))

        logger.info(f"Markdown report saved to: {markdown_file}")

    def run_all(self):
        """Run all test stages"""
        logger.info("="*70)
        logger.info("COMPREHENSIVE TEST SUITE")
        logger.info("Speech-to-Sign Language Backend")
        logger.info("="*70)

        # Stage 1: Download test data
        if not self.download_test_data():
            logger.warning("Warning: Some test data may not be available")

        # Stage 2: Unit tests
        self.run_unit_tests()

        # Stage 3: Speech recognition tests
        self.run_speech_recognition_tests()

        # Stage 4: Integration tests
        self.run_integration_tests()

        # Generate final report
        all_passed = self.generate_report()

        logger.info("\n" + "="*70)
        if all_passed:
            logger.info("✓ ALL TESTS PASSED")
        else:
            logger.info("✗ SOME TESTS FAILED - See report for details")
        logger.info("="*70)

        return 0 if all_passed else 1

def main():
    runner = TestRunner()
    sys.exit(runner.run_all())

if __name__ == "__main__":
    main()
