from .animelyrics import find_lyrics_animelyrics
from .nautiljon import find_lyrics_nautiljon
from .genius import find_lyrics_genius

def get_romaji_lyrics(title: str, artist: str) -> str:
    lyrics = find_lyrics_animelyrics(title, artist)
    if lyrics:
        return f"{title} - {artist}\n\n{lyrics}"

    lyrics = find_lyrics_nautiljon(title, artist)
    if lyrics:
        return f"{title} - {artist}\n\n{lyrics}"

    lyrics = find_lyrics_genius(title, artist)
    if lyrics:
        return f"{title} - {artist}\n\n{lyrics}"

    return f"{title} - {artist}\n\n❌ Paroles non trouvées automatiquement.\nEssaye manuellement sur Google."
