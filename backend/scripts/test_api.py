"""
Simple script to test the API endpoints
"""

import requests
import json
import base64

API_BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("\n=== Testing Health Endpoint ===")
    response = requests.get(f"{API_BASE_URL}/api/v1/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_translation():
    """Test translation endpoint"""
    print("\n=== Testing Translation Endpoint ===")

    payload = {
        "text": "Hello, how are you?",
        "target_sign_language": "ASL",
        "include_animation": False
    }

    response = requests.post(
        f"{API_BASE_URL}/api/v1/translation/translate",
        json=payload
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Original text: {data['original_text']}")
        print(f"Sign language: {data['sign_language']}")
        print(f"Gloss sequence: {data['gloss_sequence']}")
        print(f"Confidence: {data['confidence_score']}")
        print(f"Processing time: {data['processing_time_ms']}ms")
    else:
        print(f"Error: {response.text}")

    return response.status_code == 200

def test_speech_providers():
    """Test available speech providers"""
    print("\n=== Testing Speech Providers ===")

    response = requests.get(f"{API_BASE_URL}/api/v1/speech/providers")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Available providers: {data.get('providers', [])}")
    else:
        print(f"Error: {response.text}")

    return response.status_code == 200

def main():
    """Run all tests"""
    print("=" * 50)
    print("Speech to Sign Language API - Test Suite")
    print("=" * 50)

    tests = [
        ("Health Check", test_health),
        ("Translation", test_translation),
        ("Speech Providers", test_speech_providers),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\nError in {test_name}: {str(e)}")
            results.append((test_name, False))

    # Print summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{test_name}: {status}")

    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")

if __name__ == "__main__":
    main()
