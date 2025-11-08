"""
Text to Sign Language Translation Service
Handles translation of spoken language text to sign language sequences
"""

import logging
import time
import re
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.sign_dictionary import SignEntry, SignPhrase, TranslationCache
from app.config import settings

logger = logging.getLogger(__name__)

class SignLanguageGrammar:
    """
    Sign language has different grammar than spoken language.
    This class handles grammatical transformations.
    """

    @staticmethod
    def transform_to_sign_order(text: str, sign_language: str = "ASL") -> str:
        """
        Transform spoken language sentence order to sign language order
        ASL typically uses Topic-Comment structure and drops some articles/prepositions
        """
        # Basic transformations for ASL
        if sign_language == "ASL":
            # Remove common articles
            text = re.sub(r'\b(the|a|an)\b', '', text, flags=re.IGNORECASE)

            # Handle questions - move question words to end
            question_words = ['what', 'where', 'when', 'who', 'why', 'how']
            for qword in question_words:
                pattern = rf'\b{qword}\b(.+)\?'
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    rest = match.group(1).strip()
                    text = f"{rest} {qword.upper()}"
                    break

            # Remove auxiliary verbs (is, are, am, was, were)
            text = re.sub(r'\b(is|are|am|was|were)\b', '', text, flags=re.IGNORECASE)

            # Handle time expressions (move to front)
            time_words = ['yesterday', 'today', 'tomorrow', 'now', 'later']
            for time_word in time_words:
                pattern = rf'\b{time_word}\b'
                if re.search(pattern, text, re.IGNORECASE):
                    text = re.sub(pattern, '', text, flags=re.IGNORECASE)
                    text = f"{time_word.upper()} {text}"
                    break

        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @staticmethod
    def extract_key_concepts(text: str) -> List[str]:
        """Extract key concepts from text (nouns, verbs, adjectives)"""
        # Simple extraction - in production, use NLP library like spaCy
        words = text.split()
        # Filter out common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        concepts = [w for w in words if w.lower() not in stop_words]
        return concepts

class TranslationService:
    """Main translation service for text to sign language"""

    def __init__(self, db: Session):
        self.db = db
        self.grammar = SignLanguageGrammar()

    def _check_cache(self, text: str, sign_language: str) -> Optional[Dict[str, Any]]:
        """Check if translation exists in cache"""
        if not settings.CACHE_ENABLED:
            return None

        cache_entry = self.db.query(TranslationCache).filter(
            TranslationCache.source_text == text,
            TranslationCache.sign_language == sign_language
        ).first()

        if cache_entry:
            # Update usage stats
            cache_entry.usage_count += 1
            self.db.commit()

            logger.info(f"Translation cache hit for: {text[:50]}...")
            return {
                "gloss_output": cache_entry.gloss_output,
                "sign_sequence": cache_entry.sign_sequence,
                "cached": True
            }

        return None

    def _save_to_cache(
        self,
        text: str,
        sign_language: str,
        gloss_output: str,
        sign_sequence: List[Dict],
        processing_time_ms: int
    ):
        """Save translation to cache"""
        if not settings.CACHE_ENABLED:
            return

        cache_entry = TranslationCache(
            source_text=text,
            sign_language=sign_language,
            gloss_output=gloss_output,
            sign_sequence=sign_sequence,
            translation_method=settings.TRANSLATION_MODEL,
            processing_time_ms=processing_time_ms
        )
        self.db.add(cache_entry)
        self.db.commit()

    def _lookup_sign(self, word: str, sign_language: str) -> Optional[Dict[str, Any]]:
        """Look up a word in the sign dictionary"""
        # Try exact match first
        sign_entry = self.db.query(SignEntry).filter(
            SignEntry.word.ilike(word),
            SignEntry.sign_language == sign_language,
            SignEntry.is_active == True
        ).first()

        if sign_entry:
            return {
                "id": sign_entry.id,
                "word": sign_entry.word,
                "gloss": sign_entry.gloss or sign_entry.word.upper(),
                "sign_language": sign_entry.sign_language,
                "video_url": sign_entry.video_url,
                "animation_data": sign_entry.animation_data,
                "hamnosys": sign_entry.hamnosys,
                "sigml": sign_entry.sigml
            }

        # Try to fingerspell or handle as compound
        return self._handle_unknown_word(word, sign_language)

    def _handle_unknown_word(self, word: str, sign_language: str) -> Dict[str, Any]:
        """Handle words not in dictionary (fingerspelling, compounds, etc.)"""
        logger.warning(f"Word not in dictionary: {word}")

        # For now, return fingerspelling placeholder
        return {
            "id": None,
            "word": word,
            "gloss": f"FS:{word.upper()}",  # FS = fingerspell
            "sign_language": sign_language,
            "video_url": None,
            "animation_data": {"type": "fingerspelling", "letters": list(word.upper())},
            "hamnosys": None,
            "sigml": None
        }

    def _check_phrase_library(self, text: str, sign_language: str) -> Optional[Dict[str, Any]]:
        """Check if entire phrase exists in phrase library"""
        phrase_entry = self.db.query(SignPhrase).filter(
            SignPhrase.text.ilike(text),
            SignPhrase.sign_language == sign_language,
            SignPhrase.is_active == True
        ).first()

        if phrase_entry:
            # Update usage count
            phrase_entry.usage_count += 1
            self.db.commit()

            logger.info(f"Found complete phrase: {text}")
            return {
                "gloss_sequence": phrase_entry.gloss_sequence,
                "sign_sequence": phrase_entry.sign_sequence,
                "video_url": phrase_entry.video_url,
                "is_complete_phrase": True
            }

        return None

    async def translate_text(
        self,
        text: str,
        sign_language: str = "ASL",
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Translate text to sign language
        Returns gloss sequence and sign data
        """
        start_time = time.time()

        # Clean input
        text = text.strip()
        if not text:
            return {
                "original_text": text,
                "sign_language": sign_language,
                "gloss_sequence": "",
                "sign_sequence": [],
                "confidence_score": 0.0,
                "processing_time_ms": 0,
                "cached": False
            }

        # Check cache
        if use_cache:
            cached = self._check_cache(text, sign_language)
            if cached:
                processing_time = int((time.time() - start_time) * 1000)
                return {
                    "original_text": text,
                    "sign_language": sign_language,
                    "gloss_sequence": cached["gloss_output"],
                    "sign_sequence": cached["sign_sequence"],
                    "confidence_score": 0.95,
                    "processing_time_ms": processing_time,
                    "cached": True
                }

        # Check phrase library
        phrase_match = self._check_phrase_library(text, sign_language)
        if phrase_match:
            processing_time = int((time.time() - start_time) * 1000)
            return {
                "original_text": text,
                "sign_language": sign_language,
                "gloss_sequence": phrase_match["gloss_sequence"],
                "sign_sequence": phrase_match["sign_sequence"],
                "confidence_score": 1.0,
                "processing_time_ms": processing_time,
                "cached": False,
                "animation_url": phrase_match.get("video_url")
            }

        # Transform grammar
        transformed_text = self.grammar.transform_to_sign_order(text, sign_language)
        logger.info(f"Transformed: '{text}' -> '{transformed_text}'")

        # Extract words
        words = transformed_text.split()

        # Look up each word
        sign_sequence = []
        gloss_parts = []
        confidence_scores = []

        for word in words:
            if not word:
                continue

            # Clean word (remove punctuation)
            clean_word = re.sub(r'[^\w\s-]', '', word)

            # Lookup sign
            sign_data = self._lookup_sign(clean_word, sign_language)

            if sign_data:
                sign_sequence.append(sign_data)
                gloss_parts.append(sign_data["gloss"])

                # Confidence based on whether it's in dictionary
                confidence = 1.0 if sign_data["id"] is not None else 0.5
                confidence_scores.append(confidence)

        # Calculate overall confidence
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        # Create gloss sequence
        gloss_sequence = " ".join(gloss_parts)

        processing_time = int((time.time() - start_time) * 1000)

        # Save to cache
        self._save_to_cache(text, sign_language, gloss_sequence, sign_sequence, processing_time)

        return {
            "original_text": text,
            "sign_language": sign_language,
            "gloss_sequence": gloss_sequence,
            "sign_sequence": sign_sequence,
            "confidence_score": avg_confidence,
            "processing_time_ms": processing_time,
            "cached": False
        }

    async def batch_translate(
        self,
        texts: List[str],
        sign_language: str = "ASL"
    ) -> List[Dict[str, Any]]:
        """Translate multiple texts"""
        results = []
        for text in texts:
            result = await self.translate_text(text, sign_language)
            results.append(result)
        return results

def get_translation_service(db: Session) -> TranslationService:
    """Factory function to create translation service"""
    return TranslationService(db)
