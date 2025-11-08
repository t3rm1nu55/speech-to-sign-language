"""
Integration tests for complete speech-to-sign pipeline with real audio
"""

import pytest
import json
from pathlib import Path
import base64

TEST_DATA_DIR = Path(__file__).parent / "test_data"

@pytest.mark.skipif(not (TEST_DATA_DIR / "audio").exists(), reason="Test audio not downloaded")
class TestPipelineIntegration:
    """Test complete pipeline with real audio data"""

    @pytest.mark.asyncio
    async def test_complete_pipeline_speech_to_sign(self):
        """Test complete pipeline: Speech -> Text -> Sign -> Animation"""
        from app.services.speech_recognition import get_speech_service
        from app.services.translation import TranslationService
        from app.services.animation import get_animation_service
        from app.database import SessionLocal

        # Load test audio
        metadata_file = TEST_DATA_DIR / "librispeech_metadata.json"
        if not metadata_file.exists():
            pytest.skip("LibriSpeech metadata not found")

        with open(metadata_file, "r") as f:
            samples = json.load(f)

        if not samples:
            pytest.skip("No audio samples available")

        sample = samples[0]
        audio_file = TEST_DATA_DIR / "audio" / sample["audio_file"]

        if not audio_file.exists():
            pytest.skip(f"Audio file not found: {audio_file}")

        # Read audio
        with open(audio_file, "rb") as f:
            audio_data = f.read()

        # Step 1: Speech Recognition
        print("\n" + "="*60)
        print("STEP 1: Speech Recognition")
        print("="*60)

        speech_service = get_speech_service()
        speech_result = await speech_service.transcribe_audio(audio_data, "en-US")

        print(f"Reference: {sample['transcript']}")
        print(f"Recognized: {speech_result['transcript']}")
        print(f"Confidence: {speech_result['confidence']}")
        print(f"Processing time: {speech_result['processing_time_ms']}ms")

        assert len(speech_result['transcript']) > 0

        # Step 2: Translation to Sign Language
        print("\n" + "="*60)
        print("STEP 2: Translation to Sign Language")
        print("="*60)

        db = SessionLocal()
        try:
            translation_service = TranslationService(db)
            translation_result = await translation_service.translate_text(
                speech_result['transcript'],
                "ASL"
            )

            print(f"Original text: {translation_result['original_text']}")
            print(f"Gloss sequence: {translation_result['gloss_sequence']}")
            print(f"Number of signs: {len(translation_result['sign_sequence'])}")
            print(f"Confidence: {translation_result['confidence_score']:.2f}")
            print(f"Processing time: {translation_result['processing_time_ms']}ms")

            assert len(translation_result['sign_sequence']) > 0

            # Step 3: Animation Generation
            print("\n" + "="*60)
            print("STEP 3: Animation Generation")
            print("="*60)

            animation_service = get_animation_service()
            animation_result = await animation_service.generate_animation(
                translation_result['sign_sequence'],
                "ASL",
                "mp4",
                "medium",
                True,
                "avatar"
            )

            print(f"Animation URL: {animation_result['animation_url']}")
            print(f"Duration: {animation_result['duration_seconds']}s")
            print(f"Format: {animation_result['format']}")
            print(f"Processing time: {animation_result['processing_time_ms']}ms")

            # Summary
            print("\n" + "="*60)
            print("PIPELINE SUMMARY")
            print("="*60)
            total_time = (
                speech_result['processing_time_ms'] +
                translation_result['processing_time_ms'] +
                animation_result['processing_time_ms']
            )
            print(f"Total processing time: {total_time}ms ({total_time/1000:.2f}s)")
            print(f"Speech recognition: {speech_result['processing_time_ms']}ms")
            print(f"Translation: {translation_result['processing_time_ms']}ms")
            print(f"Animation: {animation_result['processing_time_ms']}ms")

            # Save results
            pipeline_result = {
                "input": {
                    "audio_file": sample["audio_file"],
                    "reference_transcript": sample["transcript"]
                },
                "speech_recognition": speech_result,
                "translation": {
                    "original_text": translation_result['original_text'],
                    "gloss_sequence": translation_result['gloss_sequence'],
                    "num_signs": len(translation_result['sign_sequence']),
                    "confidence": translation_result['confidence_score'],
                    "processing_time_ms": translation_result['processing_time_ms']
                },
                "animation": animation_result,
                "total_processing_time_ms": total_time
            }

            results_file = TEST_DATA_DIR / "pipeline_integration_results.json"
            with open(results_file, "w") as f:
                json.dump(pipeline_result, f, indent=2)

            print(f"\nResults saved to: {results_file}")

        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_api_pipeline_endpoint(self, client):
        """Test the complete pipeline API endpoint"""
        # Load test audio
        metadata_file = TEST_DATA_DIR / "librispeech_metadata.json"
        if not metadata_file.exists():
            pytest.skip("LibriSpeech metadata not found")

        with open(metadata_file, "r") as f:
            samples = json.load(f)

        if not samples:
            pytest.skip("No audio samples available")

        sample = samples[0]
        audio_file = TEST_DATA_DIR / "audio" / sample["audio_file"]

        if not audio_file.exists():
            pytest.skip(f"Audio file not found: {audio_file}")

        # Read and encode audio
        with open(audio_file, "rb") as f:
            audio_data = f.read()

        audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        # Test API endpoint
        response = client.post(
            "/api/v1/animation/speech-to-sign",
            json={
                "audio_data": audio_base64,
                "target_sign_language": "ASL",
                "output_format": "mp4",
                "include_intermediate_results": True
            }
        )

        print(f"\nAPI Response Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            print(f"Transcript: {data.get('transcript')}")
            print(f"Gloss sequence: {data.get('gloss_sequence')}")
            print(f"Animation URL: {data['animation_url']}")
            print(f"Total processing time: {data['total_processing_time_ms']}ms")

            if 'processing_breakdown' in data:
                print("\nProcessing breakdown:")
                for step, time_ms in data['processing_breakdown'].items():
                    print(f"  {step}: {time_ms}ms")

            assert 'animation_url' in data
            assert 'total_processing_time_ms' in data

        else:
            print(f"Error: {response.text}")
            # Don't fail if Whisper isn't installed yet
            if "not installed" in response.text.lower():
                pytest.skip("Whisper not installed")

    def test_batch_processing(self):
        """Test batch processing of multiple audio files"""
        # Load test phrases
        phrases_file = TEST_DATA_DIR / "test_phrases.json"
        if not phrases_file.exists():
            pytest.skip("Test phrases not found")

        with open(phrases_file, "r") as f:
            test_data = json.load(f)

        # Extract all phrases
        all_phrases = []
        for category in test_data:
            all_phrases.extend(category["phrases"])

        # Test translation of phrases
        response = self.client.post(
            "/api/v1/translation/batch-translate",
            params={"target_sign_language": "ASL"},
            json=all_phrases[:10]  # Test first 10
        )

        if response.status_code == 200:
            data = response.json()
            assert "translations" in data
            assert len(data["translations"]) == 10

            print("\nBatch Translation Results:")
            for i, translation in enumerate(data["translations"]):
                print(f"{i+1}. {translation['original_text']}")
                print(f"   -> {translation['gloss_sequence']}")
