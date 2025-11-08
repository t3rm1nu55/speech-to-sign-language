"""
Test speech recognition with real audio files from datasets
"""

import pytest
import json
import base64
from pathlib import Path
import sys

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "test_data"

def load_test_audio_metadata():
    """Load metadata for downloaded audio files"""
    metadata_files = list(TEST_DATA_DIR.glob("*_metadata.json"))

    if not metadata_files:
        pytest.skip("No test audio data found. Run: python tests/download_test_data.py")

    all_samples = []
    for metadata_file in metadata_files:
        with open(metadata_file, "r") as f:
            samples = json.load(f)
            all_samples.extend(samples)

    return all_samples

@pytest.fixture
def audio_samples():
    """Fixture to load audio sample metadata"""
    return load_test_audio_metadata()

def calculate_wer(reference, hypothesis):
    """
    Calculate Word Error Rate (WER)
    WER = (S + D + I) / N
    where S is substitutions, D is deletions, I is insertions, N is words in reference
    """
    ref_words = reference.lower().split()
    hyp_words = hypothesis.lower().split()

    # Simple Levenshtein distance for words
    d = [[0] * (len(hyp_words) + 1) for _ in range(len(ref_words) + 1)]

    for i in range(len(ref_words) + 1):
        d[i][0] = i
    for j in range(len(hyp_words) + 1):
        d[0][j] = j

    for i in range(1, len(ref_words) + 1):
        for j in range(1, len(hyp_words) + 1):
            if ref_words[i-1] == hyp_words[j-1]:
                d[i][j] = d[i-1][j-1]
            else:
                substitution = d[i-1][j-1] + 1
                insertion = d[i][j-1] + 1
                deletion = d[i-1][j] + 1
                d[i][j] = min(substitution, insertion, deletion)

    if len(ref_words) == 0:
        return 0.0 if len(hyp_words) == 0 else 1.0

    return d[len(ref_words)][len(hyp_words)] / len(ref_words)

@pytest.mark.skipif(not (TEST_DATA_DIR / "audio").exists(), reason="Test audio not downloaded")
class TestSpeechRecognitionRealAudio:
    """Test speech recognition with real audio files"""

    def test_audio_files_exist(self, audio_samples):
        """Verify test audio files exist"""
        assert len(audio_samples) > 0, "No audio samples found"

        audio_dir = TEST_DATA_DIR / "audio"
        for sample in audio_samples[:5]:  # Check first 5
            audio_file = audio_dir / sample["audio_file"]
            assert audio_file.exists(), f"Audio file not found: {audio_file}"

    @pytest.mark.asyncio
    async def test_speech_recognition_accuracy(self, audio_samples):
        """Test speech recognition accuracy with real audio"""
        from app.services.speech_recognition import get_speech_service

        speech_service = get_speech_service()
        audio_dir = TEST_DATA_DIR / "audio"

        wer_scores = []
        results = []

        # Test on first 10 samples
        for sample in audio_samples[:10]:
            audio_file = audio_dir / sample["audio_file"]

            if not audio_file.exists():
                continue

            # Read audio file
            with open(audio_file, "rb") as f:
                audio_data = f.read()

            # Transcribe
            result = await speech_service.transcribe_audio(audio_data, "en-US")

            # Calculate WER
            wer = calculate_wer(sample["transcript"], result["transcript"])
            wer_scores.append(wer)

            results.append({
                "file": sample["audio_file"],
                "reference": sample["transcript"],
                "hypothesis": result["transcript"],
                "wer": wer,
                "confidence": result["confidence"],
                "processing_time_ms": result["processing_time_ms"]
            })

            print(f"\nFile: {sample['audio_file']}")
            print(f"Reference:  {sample['transcript']}")
            print(f"Hypothesis: {result['transcript']}")
            print(f"WER: {wer:.2%}")

        # Calculate average WER
        avg_wer = sum(wer_scores) / len(wer_scores) if wer_scores else 1.0

        print(f"\n{'='*60}")
        print(f"Average WER: {avg_wer:.2%}")
        print(f"Samples tested: {len(wer_scores)}")
        print(f"{'='*60}")

        # Save detailed results
        results_file = TEST_DATA_DIR / "speech_recognition_results.json"
        with open(results_file, "w") as f:
            json.dump({
                "average_wer": avg_wer,
                "num_samples": len(wer_scores),
                "results": results
            }, f, indent=2)

        print(f"\nDetailed results saved to: {results_file}")

        # WER should be reasonable (< 50% for Whisper on clean speech)
        assert avg_wer < 0.5, f"WER too high: {avg_wer:.2%}"

    @pytest.mark.asyncio
    async def test_speech_recognition_with_base64(self, audio_samples):
        """Test speech recognition with base64 encoded audio"""
        from app.services.speech_recognition import get_speech_service

        if not audio_samples:
            pytest.skip("No audio samples available")

        speech_service = get_speech_service()
        audio_dir = TEST_DATA_DIR / "audio"

        # Test first sample
        sample = audio_samples[0]
        audio_file = audio_dir / sample["audio_file"]

        if not audio_file.exists():
            pytest.skip(f"Audio file not found: {audio_file}")

        # Read and encode audio
        with open(audio_file, "rb") as f:
            audio_data = f.read()

        audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        # Transcribe
        result = await speech_service.transcribe_from_base64(audio_base64, "en-US")

        assert "transcript" in result
        assert len(result["transcript"]) > 0
        assert result["confidence"] > 0

    @pytest.mark.asyncio
    async def test_different_providers(self, audio_samples):
        """Test different speech recognition providers if available"""
        from app.services.speech_recognition import get_speech_service

        if not audio_samples:
            pytest.skip("No audio samples available")

        speech_service = get_speech_service()
        available_providers = speech_service.get_available_providers()

        if len(available_providers) == 0:
            pytest.skip("No speech providers available")

        audio_dir = TEST_DATA_DIR / "audio"
        sample = audio_samples[0]
        audio_file = audio_dir / sample["audio_file"]

        if not audio_file.exists():
            pytest.skip(f"Audio file not found: {audio_file}")

        with open(audio_file, "rb") as f:
            audio_data = f.read()

        # Test each available provider
        for provider in available_providers:
            print(f"\nTesting provider: {provider}")
            result = await speech_service.transcribe_audio(
                audio_data,
                "en-US",
                provider=provider
            )

            assert "transcript" in result
            assert result["provider"] == provider
            print(f"  Transcript: {result['transcript'][:100]}...")
            print(f"  Processing time: {result['processing_time_ms']}ms")
