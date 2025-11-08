## Speech-to-Sign Language Backend - Test Suite

Comprehensive testing suite using real speech datasets to validate the entire pipeline.

### Overview

This test suite uses real audio data from public datasets to thoroughly test:
- Speech recognition accuracy
- Text-to-sign language translation
- Sign language animation generation
- Complete end-to-end pipeline

### Test Data Sources

1. **LibriSpeech ASR** - High-quality read speech from audiobooks
   - ~1000 hours of 16kHz English speech
   - Clean and accurate transcriptions
   - Perfect for baseline testing

2. **Common Voice** - Crowd-sourced speech from real users
   - Multiple accents and speaking styles
   - Realistic conditions (background noise, hesitations)
   - Tests robustness of the system

3. **Custom Test Phrases** - Sign language specific phrases
   - Greetings, polite expressions, questions
   - Emergency and common communication scenarios

### Quick Start

```bash
# Install test dependencies
pip install -r requirements.txt

# Download test data (one-time setup)
python tests/download_test_data.py

# Run all tests
python tests/run_comprehensive_tests.py

# Or run specific test suites
pytest tests/test_api_health.py -v
pytest tests/test_api_translation.py -v
pytest tests/test_speech_with_real_audio.py -v
pytest tests/test_integration_pipeline.py -v
```

### Test Structure

```
tests/
├── download_test_data.py         # Download real audio datasets
├── run_comprehensive_tests.py    # Main test runner with reporting
│
├── test_api_health.py            # Health check endpoints
├── test_api_translation.py        # Translation API tests
├── test_services_translation.py   # Translation service unit tests
├── test_speech_with_real_audio.py # Speech recognition with real audio
├── test_integration_pipeline.py   # End-to-end pipeline tests
│
├── test_data/
│   ├── audio/                    # Downloaded audio files
│   ├── librispeech_metadata.json # Audio file metadata
│   ├── test_phrases.json         # Test phrases for translation
│   └── *_results.json            # Test results and metrics
│
├── conftest.py                   # Pytest configuration
└── README.md                     # This file
```

### Test Categories

#### 1. API Tests
- Health check endpoints
- Translation endpoints
- Speech recognition endpoints
- Animation generation endpoints
- Batch processing

#### 2. Service Tests
- Speech recognition service
  - Multiple providers (Whisper, Google, Azure, AWS)
  - Word Error Rate (WER) calculation
  - Performance metrics

- Translation service
  - Grammar transformation (spoken → sign language)
  - Article and auxiliary verb removal
  - Question word reordering
  - Time expression handling

- Animation service
  - Avatar generation
  - Video sequence stitching
  - Multiple output formats

#### 3. Integration Tests
- Complete pipeline: Speech → Text → Sign → Animation
- API endpoint testing
- Batch processing
- Performance benchmarking

### Metrics Tracked

- **Word Error Rate (WER)**: Speech recognition accuracy
- **Processing Time**: Time for each stage and total
- **Confidence Scores**: Model confidence in predictions
- **Translation Quality**: Sign language grammar correctness

### Running Tests

#### Download Test Data

```bash
python tests/download_test_data.py
```

This will:
- Download 50 samples from LibriSpeech (~5-10 minutes)
- Attempt to download Common Voice (requires HF authentication)
- Create test phrases for translation testing

#### Run Comprehensive Test Suite

```bash
python tests/run_comprehensive_tests.py
```

This runs all tests in sequence and generates:
- Console output with detailed results
- `comprehensive_test_report.json` - Detailed JSON report
- `TEST_REPORT.md` - Markdown summary
- Individual result files for each test stage

#### Run Specific Tests

```bash
# Unit tests only
pytest tests/test_api_*.py -v

# Speech recognition only
pytest tests/test_speech_with_real_audio.py -v -s

# Integration tests only
pytest tests/test_integration_pipeline.py -v -s

# With coverage report
pytest --cov=app --cov-report=html
```

### Expected Results

#### Speech Recognition (Whisper base model on LibriSpeech clean)
- **WER**: < 5% (excellent)
- **Processing Time**: 1-3 seconds per utterance (CPU)
- **Confidence**: > 0.9

#### Translation
- **Coverage**: Should handle common phrases correctly
- **Grammar**: Proper ASL word order transformation
- **Processing Time**: < 100ms per sentence

#### Complete Pipeline
- **Total Time**: < 5 seconds for typical utterance
- **Success Rate**: > 95% for common phrases

### Test Data Volume

- **LibriSpeech**: 50 samples (~30-50MB)
- **Common Voice**: 20 samples (~10-20MB)
- **Test Phrases**: 35 common phrases
- **Total**: ~40-70MB of test data

### Troubleshooting

#### Common Voice Access Denied

Common Voice requires accepting terms of use:
1. Visit: https://huggingface.co/datasets/mozilla-foundation/common_voice_11_0
2. Accept the terms
3. Login: `huggingface-cli login`
4. Re-run download script

#### Whisper Not Installed

```bash
pip install openai-whisper
```

#### Test Data Not Found

Make sure to run the download script first:
```bash
python tests/download_test_data.py
```

#### Low Accuracy

- Check audio quality (sample rate, format)
- Verify Whisper model is loaded correctly
- Try different Whisper model sizes (tiny, base, small, medium, large)

### Continuous Integration

To use in CI/CD:

```yaml
# .github/workflows/test.yml
- name: Download test data
  run: python tests/download_test_data.py

- name: Run tests
  run: pytest tests/ -v --cov=app

- name: Generate report
  run: python tests/run_comprehensive_tests.py
```

### Contributing

When adding new tests:
1. Use real audio data when possible
2. Calculate and report relevant metrics
3. Include both positive and negative test cases
4. Document expected behavior
5. Update this README

### Resources

- **LibriSpeech**: https://huggingface.co/datasets/openslr/librispeech_asr
- **Common Voice**: https://huggingface.co/datasets/mozilla-foundation/common_voice_11_0
- **Whisper**: https://github.com/openai/whisper
- **ASL Grammar**: https://www.lifeprint.com/asl101/topics/grammar.htm
