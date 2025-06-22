#!/usr/bin/env python3
import argparse
import os
from mutagen.easyid3 import EasyID3
from lyrics_fetcher.fallback import get_romaji_lyrics

def extract_metadata(mp3_path):
    audio = EasyID3(mp3_path)
    title = audio.get("title", [None])[0]
    artist = audio.get("artist", [None])[0]
    return title, artist

def main():
    parser = argparse.ArgumentParser(description="🔎 Recherche automatique de paroles en romaji")
    parser.add_argument("mp3_path", help="Chemin vers le fichier .mp3")
    args = parser.parse_args()

    title, artist = extract_metadata(args.mp3_path)
    if not title or not artist:
        print("❌ Impossible d'extraire le titre ou l'artiste depuis le fichier mp3.")
        return

    print(f"🎵 Lecture des métadonnées : {title} - {artist}")
    result = get_romaji_lyrics(title, artist)
    print("\n========================\n")
    print(result)

if __name__ == "__main__":
    main()
