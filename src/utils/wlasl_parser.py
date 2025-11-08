"""
WLASL Dataset Parser
Parses and provides access to the WLASL (Word-Level American Sign Language) dataset.
"""

import json
import os
from typing import Dict, List, Optional
from pathlib import Path


class WLASLParser:
    """Parser for WLASL dataset JSON file."""

    def __init__(self, json_path: str = None):
        """
        Initialize the WLASL parser.

        Args:
            json_path: Path to WLASL JSON file. If None, uses default location.
        """
        if json_path is None:
            # Default to the dataset location we just downloaded
            base_dir = Path(__file__).parent.parent.parent
            json_path = base_dir / "datasets" / "WLASL" / "start_kit" / "WLASL_v0.3.json"

        self.json_path = Path(json_path)
        self.data = None
        self.gloss_index = {}  # Quick lookup: gloss -> data
        self._load_data()

    def _load_data(self):
        """Load and index the WLASL JSON data."""
        with open(self.json_path, 'r') as f:
            self.data = json.load(f)

        # Create index for fast lookup
        for entry in self.data:
            gloss = entry['gloss'].lower()
            self.gloss_index[gloss] = entry

    def get_sign_data(self, word: str) -> Optional[Dict]:
        """
        Get sign data for a specific word.

        Args:
            word: The word to look up (case-insensitive)

        Returns:
            Dictionary with sign data including all video instances, or None if not found
        """
        return self.gloss_index.get(word.lower())

    def get_video_urls(self, word: str, split: str = None, limit: int = 1) -> List[str]:
        """
        Get video URLs for a word.

        Args:
            word: The word to look up
            split: Filter by split ('train', 'test', 'val'), or None for all
            limit: Maximum number of URLs to return

        Returns:
            List of video URLs
        """
        sign_data = self.get_sign_data(word)
        if not sign_data:
            return []

        instances = sign_data.get('instances', [])

        # Filter by split if specified
        if split:
            instances = [i for i in instances if i.get('split') == split]

        # Extract URLs
        urls = [i['url'] for i in instances if 'url' in i]

        return urls[:limit] if limit else urls

    def get_all_glosses(self) -> List[str]:
        """Get list of all available glosses (words) in the dataset."""
        return list(self.gloss_index.keys())

    def search_glosses(self, query: str) -> List[str]:
        """
        Search for glosses containing the query string.

        Args:
            query: Search string

        Returns:
            List of matching glosses
        """
        query = query.lower()
        return [g for g in self.gloss_index.keys() if query in g]

    def get_dataset_stats(self) -> Dict:
        """Get statistics about the dataset."""
        total_glosses = len(self.gloss_index)
        total_instances = sum(len(entry['instances']) for entry in self.data)

        # Count by split
        splits = {'train': 0, 'test': 0, 'val': 0}
        for entry in self.data:
            for instance in entry['instances']:
                split = instance.get('split', 'unknown')
                if split in splits:
                    splits[split] += 1

        return {
            'total_glosses': total_glosses,
            'total_instances': total_instances,
            'splits': splits
        }

    def has_word(self, word: str) -> bool:
        """Check if a word exists in the dataset."""
        return word.lower() in self.gloss_index


if __name__ == "__main__":
    # Test the parser
    parser = WLASLParser()

    print("WLASL Dataset Statistics:")
    print(json.dumps(parser.get_dataset_stats(), indent=2))

    print("\nTesting word lookup:")
    test_words = ['hello', 'book', 'computer', 'love']
    for word in test_words:
        if parser.has_word(word):
            urls = parser.get_video_urls(word, limit=1)
            print(f"✓ '{word}' found - {len(urls)} video(s)")
        else:
            print(f"✗ '{word}' not found")
