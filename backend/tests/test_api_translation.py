"""
Test translation API endpoints
"""

import pytest

def test_translate_simple_text(client, db):
    """Test translating simple text to sign language"""
    response = client.post(
        "/api/v1/translation/translate",
        json={
            "text": "Hello",
            "target_sign_language": "ASL",
            "include_animation": False
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert data["original_text"] == "Hello"
    assert data["sign_language"] == "ASL"
    assert "gloss_sequence" in data
    assert "sign_sequence" in data
    assert "confidence_score" in data
    assert "processing_time_ms" in data
    assert isinstance(data["sign_sequence"], list)

def test_translate_question(client, db):
    """Test translating question to ASL (word order should change)"""
    response = client.post(
        "/api/v1/translation/translate",
        json={
            "text": "How are you?",
            "target_sign_language": "ASL"
        }
    )

    assert response.status_code == 200
    data = response.json()

    # ASL typically drops "are" and keeps HOW YOU
    gloss = data["gloss_sequence"]
    assert "HOW" in gloss
    assert "YOU" in gloss

def test_translate_with_cache(client, db):
    """Test translation caching"""
    text = "Thank you very much"

    # First request
    response1 = client.post(
        "/api/v1/translation/translate",
        json={
            "text": text,
            "target_sign_language": "ASL",
            "use_cache": True
        }
    )
    assert response1.status_code == 200
    data1 = response1.json()

    # Second request - should be cached
    response2 = client.post(
        "/api/v1/translation/translate",
        json={
            "text": text,
            "target_sign_language": "ASL",
            "use_cache": True
        }
    )
    assert response2.status_code == 200
    data2 = response2.json()

    # Results should be the same
    assert data1["gloss_sequence"] == data2["gloss_sequence"]
    # Second request might be cached (check if backend sets cached flag)

def test_translate_empty_text(client, db):
    """Test translating empty text"""
    response = client.post(
        "/api/v1/translation/translate",
        json={
            "text": "",
            "target_sign_language": "ASL"
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert data["gloss_sequence"] == ""
    assert len(data["sign_sequence"]) == 0
    assert data["confidence_score"] == 0.0

def test_translate_different_sign_languages(client, db):
    """Test translation to different sign languages"""
    text = "Hello"

    for sign_lang in ["ASL", "BSL", "ISL", "LSF"]:
        response = client.post(
            "/api/v1/translation/translate",
            json={
                "text": text,
                "target_sign_language": sign_lang
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sign_language"] == sign_lang

def test_translate_complex_sentence(client, db):
    """Test translating complex sentence"""
    response = client.post(
        "/api/v1/translation/translate",
        json={
            "text": "I am going to the store tomorrow",
            "target_sign_language": "ASL"
        }
    )

    assert response.status_code == 200
    data = response.json()

    # ASL should drop "am", "to", "the" and move "tomorrow" to front
    gloss = data["gloss_sequence"]
    assert "I" in gloss or "ME" in gloss
    assert "GO" in gloss or "GOING" in gloss
    assert "STORE" in gloss

    # Articles should be dropped
    assert " THE " not in gloss.upper()

def test_batch_translate(client, db):
    """Test batch translation"""
    texts = ["Hello", "Thank you", "Goodbye"]

    response = client.post(
        "/api/v1/translation/batch-translate",
        params={"target_sign_language": "ASL"},
        json=texts
    )

    assert response.status_code == 200
    data = response.json()

    assert "translations" in data
    assert len(data["translations"]) == len(texts)

    for translation in data["translations"]:
        assert "gloss_sequence" in translation
        assert "sign_sequence" in translation
