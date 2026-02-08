#!/usr/bin/env python3
import sys
import os
import webbrowser
from pathlib import Path
from mutagen.easyid3 import EasyID3
from googlesearch import search
import requests
from bs4 import BeautifulSoup
import re


def find_lyrics_animelyrics(title: str, artist: str) -> str:
    query = f'site:animelyrics.com "romaji lyrics" "{artist}" "{title}"'
    print(f"🔍 Recherche Google : {query}")

    # Chercher la première URL
    for url in search(query, num_results=5):
        if "animelyrics.com" in url:
            print(f"✅ URL trouvée : {url}")
            return scrape_animelyrics(url)
    return None

def scrape_animelyrics(url: str) -> str:
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.content, "html.parser")

        # Récupère TOUS les blocs <td class="romaji">
        romaji_blocks = soup.find_all("td", class_="romaji")
        if not romaji_blocks:
            print("⚠️ Aucun bloc romaji trouvé")
            return None

        lyrics_lines = []
        for block in romaji_blocks:
            raw_text = block.get_text("\n", strip=True)
            # Supprime les mentions "Lyrics from Animelyrics.com"
            cleaned_lines = [
                line for line in raw_text.splitlines()
                if "Lyrics from Animelyrics.com" not in line
            ]
            lyrics_lines.append("\n".join(cleaned_lines))

        full_lyrics = "\n\n".join(lyrics_lines)
        return full_lyrics.strip()

    except Exception as e:
        print(f"❌ Erreur scraping : {e}")
        return None

def find_lyrics_genius(title: str, artist: str) -> str:
    query = f'site:genius.com "romanized" "{artist}" "{title}"'
    print(f"🔍 [Fallback] Recherche Genius : {query}")

    for url in search(query, num_results=5):
        if "genius.com" in url:
            print(f"✅ URL trouvée (Genius): {url}")
            return scrape_genius_lyrics(url)
    return None

def scrape_genius_lyrics(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (lyrics-scraper)"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.content, "html.parser")

        containers = soup.find_all("div", {"data-lyrics-container": "true"})
        if not containers:
            return None

        lines = [div.get_text(separator="\n", strip=True) for div in containers]
        full_lyrics = "\n".join(lines).strip()

        # 🧼 Vérifie si c’est un placeholder
        if "to be transcribed" in full_lyrics.lower():
            return None

        return full_lyrics

    except Exception as e:
        print(f"❌ Erreur scraping Genius : {e}")
        return None

def extract_metadata(mp3_path: str):
    try:
        audio = EasyID3(mp3_path)
        title = audio.get('title', ['Unknown Title'])[0]
        artist = audio.get('artist', ['Unknown Artist'])[0]
        return title, artist
    except Exception as e:
        print(f"Erreur lors de l'extraction des métadonnées : {e}")
        return "Unknown Title", "Unknown Artist"


def get_romaji_lyrics(title: str, artist: str) -> str:
    # Essai 1 : animelyrics
    lyrics = find_lyrics_animelyrics(title, artist)
    if lyrics:
        return f"{title} - {artist}\n\n{lyrics}"

    # Fallback 2 : Genius
    lyrics = find_lyrics_genius(title, artist)
    if lyrics:
        return f"{title} - {artist}\n\n{lyrics}"

    return f"{title} - {artist}\n\n❌ Paroles non trouvées automatiquement.\nEssaye manuellement sur Google."


def write_lyrics_file(title: str, artist: str, content: str):
    filename = f"lyrics_{artist}_{title}.txt".replace(" ", "_")
    filepath = Path.cwd() / filename
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"📝 Fichier créé : {filepath}")
    os.system(f"xdg-open '{filepath}'")  # ouvre dans l'éditeur par défaut (Linux)

def main():
    if len(sys.argv) != 2:
        print("Usage: python lyrics_fetcher_poc.py <chemin_du_fichier_mp3>")
        return

    mp3_path = sys.argv[1]
    if not os.path.exists(mp3_path):
        print(f"❌ Fichier non trouvé : {mp3_path}")
        return

    title, artist = extract_metadata(mp3_path)
    lyrics = get_romaji_lyrics(title, artist)
    write_lyrics_file(title, artist, lyrics)


if __name__ == "__main__":
    main()
