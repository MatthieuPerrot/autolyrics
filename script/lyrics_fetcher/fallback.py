from .animelyrics import find_lyrics_animelyrics
from .nautiljon import find_lyrics_nautiljon
from .genius import find_lyrics_genius

def get_romaji_lyrics(title: str, artists: list) -> str:
    lyrics = find_lyrics_animelyrics(title, artists)
    if lyrics:
        return f"{title} - {' '.join(artists)}\n\n{lyrics}"

    lyrics = find_lyrics_nautiljon(title, artists)
    if lyrics:
        return f"{title} - {' '.join(artists)}\n\n{lyrics}"

    lyrics = find_lyrics_genius(title, artists)
    if lyrics:
        return f"{title} - {' '.join(artists)}\n\n{lyrics}"

    return f"{title} - {' '.join(artists)}\n\n❌ Paroles non trouvées automatiquement.\nEssaye manuellement sur Google."
