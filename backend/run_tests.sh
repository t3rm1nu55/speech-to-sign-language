#!/bin/bash

# Speech-to-Sign Language Backend Test Runner

set -e

echo "========================================"
echo "Speech-to-Sign Language Backend Tests"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if in backend directory
if [ ! -f "main.py" ]; then
    echo -e "${RED}Error: Please run this script from the backend directory${NC}"
    exit 1
fi

# Parse arguments
DOWNLOAD_DATA=false
QUICK_TEST=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --download)
            DOWNLOAD_DATA=true
            shift
            ;;
        --quick)
            QUICK_TEST=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "Usage: ./run_tests.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --download    Download test data before running tests"
            echo "  --quick       Run only quick tests (skip heavy audio tests)"
            echo "  -v, --verbose Run tests with verbose output"
            echo "  -h, --help    Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Check Python dependencies
echo "Checking dependencies..."
python -c "import pytest" 2>/dev/null || {
    echo -e "${YELLOW}Installing test dependencies...${NC}"
    pip install pytest pytest-asyncio pytest-cov datasets soundfile
}

# Download test data if requested
if [ "$DOWNLOAD_DATA" = true ]; then
    echo ""
    echo -e "${YELLOW}Downloading test data...${NC}"
    python tests/download_test_data.py
fi

# Check if test data exists
if [ ! -d "tests/test_data/audio" ] && [ "$QUICK_TEST" = false ]; then
    echo ""
    echo -e "${YELLOW}Warning: Test audio data not found.${NC}"
    echo "Some tests will be skipped."
    echo "Run with --download to download test data, or use --quick for fast tests only."
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "========================================"
echo "Running Tests"
echo "========================================"
echo ""

# Set pytest options
PYTEST_OPTS="-v"
if [ "$VERBOSE" = true ]; then
    PYTEST_OPTS="$PYTEST_OPTS -s"
fi

if [ "$QUICK_TEST" = true ]; then
    echo -e "${YELLOW}Running quick tests only...${NC}"
    python -m pytest tests/test_api_health.py tests/test_api_translation.py tests/test_services_translation.py $PYTEST_OPTS
else
    echo -e "${YELLOW}Running comprehensive test suite...${NC}"
    python tests/run_comprehensive_tests.py
fi

TEST_EXIT_CODE=$?

echo ""
echo "========================================"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
fi
echo "========================================"

# Show test results location if they exist
if [ -f "tests/test_data/TEST_REPORT.md" ]; then
    echo ""
    echo "Test reports available:"
    echo "  - tests/test_data/TEST_REPORT.md"
    echo "  - tests/test_data/comprehensive_test_report.json"
fi

exit $TEST_EXIT_CODE
