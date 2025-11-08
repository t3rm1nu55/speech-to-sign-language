"""
Download real speech datasets with transcriptions for testing
Uses LibriSpeech and other public datasets from Hugging Face
"""

import os
import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_librispeech_samples(num_samples=50, output_dir="tests/test_data/audio"):
    """
    Download sample audio files from LibriSpeech dataset

    Args:
        num_samples: Number of samples to download
        output_dir: Directory to save audio files
    """
    try:
        from datasets import load_dataset
        import soundfile as sf
        import numpy as np
    except ImportError:
        logger.error("Required libraries not installed. Run: pip install datasets soundfile")
        return False

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info("Loading LibriSpeech dataset...")
    # Load test.clean subset (smaller, high quality)
    dataset = load_dataset("openslr/librispeech_asr", "clean", split="test.clean", streaming=True)

    samples_data = []
    count = 0

    logger.info(f"Downloading {num_samples} audio samples...")

    for idx, sample in enumerate(dataset):
        if count >= num_samples:
            break

        try:
            # Get audio data
            audio = sample["audio"]
            text = sample["text"]
            sample_id = sample.get("id", f"sample_{idx}")

            # Save audio file
            audio_filename = f"librispeech_{sample_id}.wav"
            audio_filepath = output_path / audio_filename

            # Write audio to WAV file
            sf.write(str(audio_filepath), audio["array"], audio["sampling_rate"])

            # Store metadata
            samples_data.append({
                "id": sample_id,
                "audio_file": audio_filename,
                "transcript": text,
                "source": "librispeech_test_clean",
                "sampling_rate": audio["sampling_rate"],
                "speaker_id": sample.get("speaker_id"),
                "duration_seconds": len(audio["array"]) / audio["sampling_rate"]
            })

            count += 1
            if count % 10 == 0:
                logger.info(f"Downloaded {count}/{num_samples} samples...")

        except Exception as e:
            logger.error(f"Error processing sample {idx}: {str(e)}")
            continue

    # Save metadata
    metadata_file = output_path / "librispeech_metadata.json"
    with open(metadata_file, "w") as f:
        json.dump(samples_data, f, indent=2)

    logger.info(f"Successfully downloaded {len(samples_data)} samples")
    logger.info(f"Metadata saved to {metadata_file}")

    return True

def download_common_voice_samples(num_samples=20, output_dir="tests/test_data/audio", language="en"):
    """
    Download sample audio files from Common Voice dataset
    Note: Requires accepting terms of use on Hugging Face

    Args:
        num_samples: Number of samples to download
        output_dir: Directory to save audio files
        language: Language code (en, es, fr, etc.)
    """
    try:
        from datasets import load_dataset
        import soundfile as sf
    except ImportError:
        logger.error("Required libraries not installed. Run: pip install datasets soundfile")
        return False

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        logger.info(f"Loading Common Voice dataset for {language}...")
        # Note: User must accept terms on HF Hub first
        dataset = load_dataset(
            "mozilla-foundation/common_voice_11_0",
            language,
            split="test",
            streaming=True,
            use_auth_token=True  # Requires HF authentication
        )

        samples_data = []
        count = 0

        logger.info(f"Downloading {num_samples} audio samples...")

        for idx, sample in enumerate(dataset):
            if count >= num_samples:
                break

            try:
                # Get audio data
                audio = sample["audio"]
                text = sample["sentence"]

                # Save audio file
                audio_filename = f"commonvoice_{language}_{idx}.wav"
                audio_filepath = output_path / audio_filename

                # Write audio to WAV file
                sf.write(str(audio_filepath), audio["array"], audio["sampling_rate"])

                # Store metadata
                samples_data.append({
                    "id": f"cv_{language}_{idx}",
                    "audio_file": audio_filename,
                    "transcript": text,
                    "source": f"common_voice_{language}",
                    "sampling_rate": audio["sampling_rate"],
                    "age": sample.get("age"),
                    "gender": sample.get("gender"),
                    "accent": sample.get("accent"),
                    "duration_seconds": len(audio["array"]) / audio["sampling_rate"]
                })

                count += 1
                if count % 5 == 0:
                    logger.info(f"Downloaded {count}/{num_samples} samples...")

            except Exception as e:
                logger.error(f"Error processing sample {idx}: {str(e)}")
                continue

        # Save metadata
        metadata_file = output_path / f"commonvoice_{language}_metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(samples_data, f, indent=2)

        logger.info(f"Successfully downloaded {len(samples_data)} samples")
        logger.info(f"Metadata saved to {metadata_file}")

        return True

    except Exception as e:
        logger.error(f"Error downloading Common Voice: {str(e)}")
        logger.info("You may need to:")
        logger.info("1. Accept terms at: https://huggingface.co/datasets/mozilla-foundation/common_voice_11_0")
        logger.info("2. Login with: huggingface-cli login")
        return False

def create_test_phrases():
    """
    Create test phrases for sign language translation testing
    These are common phrases that should be in sign language dictionaries
    """
    test_phrases = [
        {
            "category": "greetings",
            "phrases": [
                "Hello",
                "Good morning",
                "Good afternoon",
                "Good evening",
                "How are you",
                "Nice to meet you",
                "Welcome"
            ]
        },
        {
            "category": "polite",
            "phrases": [
                "Please",
                "Thank you",
                "You're welcome",
                "Excuse me",
                "I'm sorry",
                "No problem"
            ]
        },
        {
            "category": "questions",
            "phrases": [
                "What is your name",
                "Where are you from",
                "How old are you",
                "What time is it",
                "Where is the bathroom",
                "Can you help me"
            ]
        },
        {
            "category": "emergency",
            "phrases": [
                "I need help",
                "Call the police",
                "Call an ambulance",
                "I am lost",
                "Emergency"
            ]
        },
        {
            "category": "basic_communication",
            "phrases": [
                "Yes",
                "No",
                "I understand",
                "I don't understand",
                "Please repeat",
                "Speak slowly please"
            ]
        }
    ]

    output_path = Path("tests/test_data")
    output_path.mkdir(parents=True, exist_ok=True)

    with open(output_path / "test_phrases.json", "w") as f:
        json.dump(test_phrases, f, indent=2)

    logger.info(f"Created test phrases file with {sum(len(c['phrases']) for c in test_phrases)} phrases")

def main():
    """Main function to download all test data"""
    logger.info("=" * 60)
    logger.info("Downloading Speech Test Data")
    logger.info("=" * 60)

    # Create test phrases
    logger.info("\n1. Creating test phrases...")
    create_test_phrases()

    # Download LibriSpeech samples
    logger.info("\n2. Downloading LibriSpeech samples...")
    success_librispeech = download_librispeech_samples(num_samples=50)

    # Try to download Common Voice (may require authentication)
    logger.info("\n3. Attempting to download Common Voice samples...")
    success_cv = download_common_voice_samples(num_samples=20)

    logger.info("\n" + "=" * 60)
    logger.info("Download Summary")
    logger.info("=" * 60)
    logger.info(f"LibriSpeech: {'✓ Success' if success_librispeech else '✗ Failed'}")
    logger.info(f"Common Voice: {'✓ Success' if success_cv else '✗ Failed or requires authentication'}")
    logger.info("\nTest data is ready for use!")
    logger.info("Run: pytest tests/ -v to run tests")

if __name__ == "__main__":
    main()
