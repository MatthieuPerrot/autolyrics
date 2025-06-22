# Placeholders pour l'instant. Futur : détection de langue, conversion romaji, logs, etc.

def is_romaji(text: str) -> bool:
    return all(ord(c) < 128 for c in text)


def detect_script(text: str) -> str:
    # Très simplifié
    if any('\u3040' <= c <= '\u30ff' for c in text):
        return 'japanese'
    elif any('\u1100' <= c <= '\u11FF' or '\uAC00' <= c <= '\uD7AF' for c in text):
        return 'korean'
    return 'latin'


