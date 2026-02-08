#!/usr/bin/env python3
import argparse
import os
import sys # Pour sys.executable
import subprocess # Pour appeler sync_lyrics.py
from mutagen.easyid3 import EasyID3
from lyrics_fetcher.fallback import get_romaji_lyrics

_JAPANESE_CODES = {"ja", "jpn", "japanese"}


def is_japanese_language(lang_code: str) -> bool:
    """Return True if the language code refers to Japanese."""
    return lang_code.strip().lower() in _JAPANESE_CODES


def extract_metadata(mp3_path):
    audio = EasyID3(mp3_path)
    title = audio.get("title", [None])[0]
    artists = audio.get("artist", [None])[0]
    if artists is not None: artists = artists.split('/')
    language = audio.get("language", [None])[0]
    return title, artists, language

def main():
    parser = argparse.ArgumentParser(description="🔎 Recherche automatique de paroles en romaji et synchronisation optionnelle.")
    parser.add_argument("mp3_path", help="Chemin vers le fichier .mp3")
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Lancer la synchronisation manuelle des paroles après les avoir récupérées."
    )
    parser.add_argument(
        "-o", "--output_lyrics_txt",
        help="Chemin pour sauvegarder les paroles brutes .txt (optionnel, défaut: <nom_mp3>.txt)"
    )
    args = parser.parse_args()

    mp3_file_path = args.mp3_path
    title, artists, language = extract_metadata(mp3_file_path)
    if not title or not artists or len(artists) == 0:
        print("❌ Impossible d'extraire le titre ou l'artiste depuis le fichier mp3.")
        return

    print(f"🎵 Lecture des métadonnées : {title} - {artists}")
    if language and not is_japanese_language(language):
        print(f"⚠️ MP3 language tag: '{language}' (not Japanese). Romaji search may not find results.")
    lyrics_text = get_romaji_lyrics(title, artists)

    if not lyrics_text or lyrics_text.strip() == "LYRICS NOT FOUND":
        print("❌ Paroles non trouvées. Impossible de continuer avec la synchronisation.")
        return

    print("\n========================\n")
    print(lyrics_text)
    print("\n========================\n")

    # Sauvegarde des paroles brutes
    if args.output_lyrics_txt:
        lyrics_txt_path = args.output_lyrics_txt
    else:
        base, _ = os.path.splitext(mp3_file_path)
        lyrics_txt_path = f"{base}.txt"

    try:
        with open(lyrics_txt_path, 'w', encoding='utf-8') as f:
            f.write(lyrics_text)
        print(f"✅ Paroles brutes sauvegardées dans : {lyrics_txt_path}")
    except IOError as e:
        print(f"❌ Erreur lors de la sauvegarde des paroles brutes : {e}")
        return

    # Lancer la synchronisation si demandé
    if args.sync:
        print(f"\n🔄 Lancement de la synchronisation pour {mp3_file_path} et {lyrics_txt_path}...")

        # Déterminer le chemin du script sync_lyrics.py
        # On suppose qu'il est dans le même répertoire que ce script (lyrics_fetcher_cli.py)
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        sync_script_path = os.path.join(current_script_dir, "sync_lyrics.py")

        if not os.path.exists(sync_script_path):
            print(f"❌ Erreur : Le script de synchronisation '{sync_script_path}' est introuvable.")
            return

        try:
            # sys.executable est le chemin vers l'interpréteur Python courant
            command = [sys.executable, sync_script_path, mp3_file_path, lyrics_txt_path]
            print(f"Exécution de : {' '.join(command)}")

            # Utiliser Popen pour une meilleure gestion si on veut capturer stdout/stderr en temps réel plus tard
            # Pour l'instant, run suffit et est plus simple
            process = subprocess.run(command, check=False) # check=False pour gérer nous-même les erreurs

            if process.returncode == 0:
                print("✅ Synchronisation terminée avec succès.")
            else:
                print(f"⚠️ Le script de synchronisation s'est terminé avec le code d'erreur : {process.returncode}")

        except FileNotFoundError:
            print(f"❌ Erreur : L'interpréteur Python '{sys.executable}' ou le script '{sync_script_path}' est introuvable.")
        except subprocess.CalledProcessError as e:
            print(f"❌ Erreur lors de l'exécution du script de synchronisation : {e}")
        except Exception as e:
            print(f"❌ Une erreur inattendue est survenue lors du lancement de la synchronisation : {e}")
    else:
        print("\nPour synchroniser ces paroles, relancez avec l'option --sync.")

if __name__ == "__main__":
    main()
