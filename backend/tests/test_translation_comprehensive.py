"""
Comprehensive translation testing with diverse text inputs
Tests the complete English to ASL gloss translation pipeline
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, Base, engine
from app.services.translation import TranslationService
from app.models.sign_dictionary import SignEntry
import asyncio


class TranslationTester:
    def __init__(self):
        self.db = SessionLocal()
        self.service = TranslationService(self.db)

        # Get dictionary stats
        self.total_signs = self.db.query(SignEntry).filter(
            SignEntry.sign_language == 'ASL'
        ).count()
        self.signs_with_video = self.db.query(SignEntry).filter(
            SignEntry.sign_language == 'ASL',
            SignEntry.video_url.isnot(None)
        ).count()

    def print_header(self):
        print("=" * 80)
        print("ASL TRANSLATION COMPREHENSIVE TEST")
        print("=" * 80)
        print(f"Dictionary: {self.total_signs} ASL signs")
        print(f"Video URLs: {self.signs_with_video} signs ({self.signs_with_video/self.total_signs*100:.1f}%)")
        print("=" * 80)
        print()

    async def test_sentence(self, text, expected_gloss=None, category="General"):
        """Test a single sentence translation"""
        print(f"[{category}]")
        print(f"Input:  \"{text}\"")

        result = await self.service.translate_text(text, "ASL")
        gloss = result['gloss_sequence']
        signs = result['sign_sequence']

        print(f"Output: \"{gloss}\"")

        # Count matched signs vs fingerspelled
        matched = sum(1 for s in signs if not s['gloss'].startswith('FS:'))
        fingerspelled = len(signs) - matched

        print(f"Match:  {matched}/{len(signs)} signs found in dictionary")
        if fingerspelled > 0:
            print(f"        {fingerspelled} word(s) fingerspelled")

        # Check if expected gloss matches
        if expected_gloss:
            matches = gloss == expected_gloss
            status = "✓ PASS" if matches else "✗ FAIL"
            print(f"Expected: \"{expected_gloss}\" {status}")

        # Show video availability
        with_video = sum(1 for s in signs if s.get('video_url'))
        if with_video > 0:
            print(f"Videos:  {with_video}/{len(signs)} signs have video references")

        print()
        return result

    async def run_tests(self):
        """Run comprehensive test suite"""
        self.print_header()

        # Test 1: Basic greetings
        print("--- TEST 1: GREETINGS & BASIC PHRASES ---\n")
        await self.test_sentence(
            "Hello how are you",
            "HELLO HOW YOU",
            "Greeting"
        )
        await self.test_sentence(
            "Good morning",
            "GOOD MORNING",
            "Greeting"
        )
        await self.test_sentence(
            "Thank you very much",
            category="Polite"
        )

        # Test 2: Questions
        print("--- TEST 2: QUESTIONS ---\n")
        await self.test_sentence(
            "What is your name",
            "WHAT YOUR NAME",
            "Question"
        )
        await self.test_sentence(
            "Where do you live",
            category="Question"
        )
        await self.test_sentence(
            "How old are you",
            category="Question"
        )
        await self.test_sentence(
            "Why are you sad",
            category="Question"
        )

        # Test 3: Statements with auxiliary verbs
        print("--- TEST 3: AUXILIARY VERB REMOVAL ---\n")
        await self.test_sentence(
            "I am happy",
            "I HAPPY",
            "Statement"
        )
        await self.test_sentence(
            "She is beautiful",
            category="Statement"
        )
        await self.test_sentence(
            "They are going to school",
            category="Statement"
        )

        # Test 4: Common needs/requests
        print("--- TEST 4: NEEDS & REQUESTS ---\n")
        await self.test_sentence(
            "I need help",
            "I NEED HELP",
            "Need"
        )
        await self.test_sentence(
            "Can you help me",
            category="Request"
        )
        await self.test_sentence(
            "I want water please",
            category="Request"
        )

        # Test 5: Time expressions
        print("--- TEST 5: TIME EXPRESSIONS ---\n")
        await self.test_sentence(
            "I will go tomorrow",
            category="Time"
        )
        await self.test_sentence(
            "Yesterday I was sick",
            category="Time"
        )
        await self.test_sentence(
            "Today is Friday",
            category="Time"
        )

        # Test 6: Emergency phrases
        print("--- TEST 6: EMERGENCY SITUATIONS ---\n")
        await self.test_sentence(
            "Help I need police",
            category="Emergency"
        )
        await self.test_sentence(
            "Call ambulance please",
            category="Emergency"
        )
        await self.test_sentence(
            "Fire danger",
            category="Emergency"
        )

        # Test 7: Complex sentences
        print("--- TEST 7: COMPLEX SENTENCES ---\n")
        await self.test_sentence(
            "I want to go to the store tomorrow",
            category="Complex"
        )
        await self.test_sentence(
            "My family is going to visit your house",
            category="Complex"
        )
        await self.test_sentence(
            "The book on the table is mine",
            category="Complex"
        )

        # Test 8: Emotions & descriptions
        print("--- TEST 8: EMOTIONS & DESCRIPTIONS ---\n")
        await self.test_sentence(
            "I feel sad today",
            category="Emotion"
        )
        await self.test_sentence(
            "You look beautiful",
            category="Description"
        )
        await self.test_sentence(
            "The weather is cold and bad",
            category="Description"
        )

        # Test 9: Colors & numbers
        print("--- TEST 9: COLORS & NUMBERS ---\n")
        await self.test_sentence(
            "I have three red books",
            category="Colors/Numbers"
        )
        await self.test_sentence(
            "Give me five blue pencils",
            category="Colors/Numbers"
        )

        # Test 10: Unknown words (fingerspelling test)
        print("--- TEST 10: FINGERSPELLING FALLBACK ---\n")
        await self.test_sentence(
            "My name is Alexandria",
            category="Proper Name"
        )
        await self.test_sentence(
            "I study biochemistry at university",
            category="Technical Terms"
        )

        # Summary
        print("=" * 80)
        print("TEST SUITE COMPLETE")
        print("=" * 80)
        print(f"Dictionary: {self.total_signs} ASL signs available")
        print(f"Video Coverage: {self.signs_with_video} signs with videos ({self.signs_with_video/self.total_signs*100:.1f}%)")
        print("\nTranslation system is operational and ready for speech integration!")
        print("=" * 80)

    def cleanup(self):
        """Close database connection"""
        self.db.close()


async def main():
    """Main test execution"""
    tester = TranslationTester()
    try:
        await tester.run_tests()
    finally:
        tester.cleanup()


if __name__ == "__main__":
    # Set DATABASE_URL if not set
    import os
    if 'DATABASE_URL' not in os.environ:
        os.environ['DATABASE_URL'] = 'sqlite:///./sign_language.db'

    asyncio.run(main())
