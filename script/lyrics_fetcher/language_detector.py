"""Language detection utility for lyrics"""

import re
import unicodedata


def is_likely_english(text: str) -> bool:
    """
    Detect if text is likely English translation vs romaji.

    Returns True if text appears to be English.
    """
    # Common English words that are NOT romaji
    # Focus on high-frequency function words
    english_words = {
        'the', 'and', 'you', 'are', 'is', 'was', 'were', 'been', 'have', 'has',
        'had', 'will', 'would', 'should', 'could', 'can', 'may', 'might',
        'with', 'without', 'from', 'into', 'onto', 'through', 'over', 'under',
        'my', 'your', 'his', 'her', 'their', 'our',
        'as', 'if', 'when', 'where', 'why', 'how',
        'this', 'that', 'these', 'those',
        'all', 'some', 'any', 'each', 'every', 'both', 'neither',
        'much', 'many', 'more', 'most', 'few', 'less', 'least',
        'not', 'never', 'always', 'sometimes', 'often',
        'it', 'its', 'they', 'them', 'me', 'him', 'us',
        'at', 'by', 'for', 'in', 'on', 'of', 'off', 'out', 'up', 'down',
    }

    # Very specific English phrases that never appear in romaji
    english_phrases = [
        r"\bthe\s+\w+",          # "the [word]"
        r"\b(as|if)\s+\w+",      # "as/if [word]"
        r"\binto\s+(the|my|your|his|her|their|our)",
        r"\bin\s+(the|my|your|his|her|their|our)",
        r"'(s|re|ve|ll|d|t)\b", # contractions: it's, you're, I've, etc.
    ]

    # Common romaji particles and verb endings (very distinctive)
    romaji_indicators = [
        r'\b(wa|wo|ga|no|ni|de|to|ka|mo|ne|yo|sa|ze|na|tte|nda|kedo)\b',
        r'\b(desu|masu|mashita|masen|deshita)\b',
        r'\b(watashi|anata|kimi|ore|boku|kare|kanojo)\b',
        r'\b(kono|sono|ano|konna|sonna|anna)\b',
        r'\b\w+(ru|ta|te|shi|tsu|chi|tsu|dzu)\b',  # verb/adjective endings
    ]

    # Normalize text
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)

    if len(words) < 3:  # Too short to determine
        return False

    # Count English words
    english_count = sum(1 for word in words if word in english_words)
    english_ratio = english_count / len(words)

    # Count English phrases
    english_phrase_count = sum(1 for pattern in english_phrases if re.search(pattern, text_lower))

    # Count romaji indicators
    romaji_count = sum(1 for pattern in romaji_indicators if re.search(pattern, text_lower))

    # Decision logic:
    # 1. Romaji indicators take priority — mixed English/romaji is common in J-pop
    if romaji_count > 0:
        return False

    # 2. If no romaji found, English phrases confirm English text
    if english_phrase_count > 0:
        return True

    # 3. If more than 15% are common English words, likely English
    if english_ratio > 0.15:
        return True

    # 4. Default to checking if text has typical English patterns
    # English often has articles (a, an, the) which romaji never has
    if re.search(r'\b(a|an|the)\s+\w+', text_lower):
        return True

    return False


def contains_japanese_characters(text: str) -> bool:
    """
    Detect if text contains Japanese characters (hiragana, katakana, kanji).

    Returns True if text contains Japanese characters.
    """
    for char in text:
        # Check for Hiragana: U+3040 - U+309F
        # Check for Katakana: U+30A0 - U+30FF
        # Check for Kanji (CJK): U+4E00 - U+9FFF
        code_point = ord(char)
        if (0x3040 <= code_point <= 0x309F or  # Hiragana
            0x30A0 <= code_point <= 0x30FF or  # Katakana
            0x4E00 <= code_point <= 0x9FFF):   # Kanji (CJK)
            return True
    return False


def is_likely_romaji(text: str) -> bool:
    """
    Detect if text is likely romaji.

    Returns True if text appears to be romaji (not English, not Japanese characters).
    """
    # Reject if it's English
    if is_likely_english(text):
        return False

    # Reject if it contains Japanese characters (kanji/hiragana/katakana)
    if contains_japanese_characters(text):
        return False

    # If it's neither English nor Japanese characters, it's likely romaji
    return True


def filter_romaji_only(text_blocks: list[str]) -> list[str]:
    """
    Filter a list of text blocks to keep only romaji ones.

    Args:
        text_blocks: List of text strings to filter

    Returns:
        List of text blocks that appear to be romaji
    """
    romaji_blocks = []

    for block in text_blocks:
        if not block.strip():
            continue

        if is_likely_romaji(block):
            romaji_blocks.append(block)

    return romaji_blocks
