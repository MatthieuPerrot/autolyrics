#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour synchroniser des paroles non synchronisées avec un fichier audio MP3
et générer un fichier de paroles synchronisées au format LRC (Enhanced LRC).
"""

import argparse
import os
import time
import pygame # Ajout de pygame
from mutagen.easyid3 import EasyID3 # Ajout pour les métadonnées MP3

class LyricsSyncer:
    """
    Classe pour gérer la synchronisation des paroles.
    """
    def __init__(self, mp3_path, lyrics_path, output_path=None):
        self.mp3_path = mp3_path
        self.lyrics_path = lyrics_path
        self.output_path = output_path or self._generate_output_path()

        if not os.path.exists(self.mp3_path):
            raise FileNotFoundError(f"Fichier MP3 non trouvé : {self.mp3_path}")
        if not os.path.exists(self.lyrics_path):
            raise FileNotFoundError(f"Fichier de paroles non trouvé : {self.lyrics_path}")

        self.raw_lyrics_lines = self._load_raw_lyrics()
        self.synced_lyrics = [] # Contiendra les lignes [mm:ss.xx]Paroles

    def _generate_output_path(self):
        """Génère un chemin de sortie par défaut pour le fichier .lrc."""
        base, _ = os.path.splitext(self.mp3_path)
        return f"{base}.lrc"

    def _load_raw_lyrics(self):
        """Charge les lignes de paroles depuis le fichier .txt."""
        with open(self.lyrics_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        return lines

    def _format_time(self, seconds_float):
        """Convertit un temps en secondes (float) au format mm:ss.xx."""
        minutes = int(seconds_float // 60)
        seconds = int(seconds_float % 60)
        hundredths = int((seconds_float - (minutes * 60) - seconds) * 100)
        return f"{minutes:02d}:{seconds:02d}.{hundredths:02d}"

    def sync_manually_per_line(self):
        """
        Permet à l'utilisateur de synchroniser les paroles manuellement ligne par ligne.
        L'utilisateur appuie sur une touche pour marquer le début de chaque ligne.
        """
        print(f"Chargement du MP3 : {self.mp3_path}")
        print("Préparez-vous à synchroniser les paroles.")
        print("Appuyez sur Entrée au moment où chaque ligne de parole commence.")
        print("Appuyez sur 'q' puis Entrée pour quitter en cours de synchronisation.")
        print("-" * 30)

        playback_started = False
        # Initialisation de start_time pour le cas où pygame échoue complètement
        start_time = time.time()

        try:
            # Essai d'initialisation de pygame.mixer avec des paramètres spécifiques
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            except pygame.error as e_init_specific:
                print(f"Avertissement : Erreur lors de l'initialisation de pygame.mixer (paramètres spécifiques): {e_init_specific}")
                print("Tentative d'initialisation avec les paramètres par défaut.")
                pygame.mixer.init() # Essai avec les paramètres par défaut si le premier échoue

            # Si l'initialisation a réussi, on charge et joue la musique
            pygame.mixer.music.load(self.mp3_path)
            print(f"Lecture de : {self.mp3_path}")
            pygame.mixer.music.play()
            start_time = time.time() # Récupérer le temps de début réel APRES le play()
            playback_started = True

        except pygame.error as e_pygame:
            # Cette exception attrape les erreurs de init() par défaut ou de load()/play()
            print(f"Erreur Pygame : {e_pygame}")
            print("La synchronisation se fera sans lecture audio réelle (simulation du temps).")
            # start_time est déjà initialisé pour la simulation
            # playback_started reste False

        for i, line in enumerate(self.raw_lyrics_lines):
            print(f"\nProchaine ligne ({i+1}/{len(self.raw_lyrics_lines)}):")
            print(f"🎵 {line} 🎵")

            user_input = input("Appuyez sur Entrée ou 'q' pour quitter: ")
            if user_input.lower() == 'q':
                print("Synchronisation annulée par l'utilisateur.")
                self.synced_lyrics = [] # Vider pour ne pas sauvegarder un fichier partiel
                break

            current_timestamp_sec = time.time() - start_time
            formatted_time = self._format_time(current_timestamp_sec)
            self.synced_lyrics.append(f"[{formatted_time}]{line}")
            print(f"-> Ligne enregistrée à {formatted_time}")

        if playback_started:
            pygame.mixer.music.stop()
            pygame.mixer.quit()

        print("\nSynchronisation terminée.")
        self._save_lrc_file()

    def _save_lrc_file(self):
        """Sauvegarde les paroles synchronisées dans un fichier .lrc."""
        if not self.synced_lyrics:
            print("Aucune parole synchronisée à sauvegarder.")
            return

        # Ajout de tags d'identification
        lrc_content = []

        title = "Unknown Title"
        artist = "Unknown Artist"
        album = "Unknown Album"

        try:
            audio_meta = EasyID3(self.mp3_path)
            if "title" in audio_meta:
                title = audio_meta["title"][0]
            if "artist" in audio_meta:
                artist = audio_meta["artist"][0]
            if "album" in audio_meta:
                album = audio_meta["album"][0]
        except Exception as e:
            print(f"Avertissement : Impossible de lire les métadonnées ID3 du MP3 : {e}")

        lrc_content.append(f"[ti:{title}]")
        lrc_content.append(f"[ar:{artist}]")
        lrc_content.append(f"[al:{album}]")
        lrc_content.append(f"[by:Autolyrics Syncer v0.1]")

        lrc_content.extend(self.synced_lyrics)

        with open(self.output_path, 'w', encoding='utf-8') as f:
            for line in lrc_content:
                f.write(line + "\n")
        print(f"Fichier LRC sauvegardé : {self.output_path}")

    def sync_manually_per_word(self):
        """
        Permet à l'utilisateur de synchroniser les paroles mot par mot.
        (Plus complexe, à implémenter dans une future itération)
        """
        print("La synchronisation mot par mot n'est pas encore implémentée.")
        # Logique possible:
        # 1. Afficher la ligne entière.
        # 2. Lire la ligne (synthèse vocale ou le chanteur).
        # 3. L'utilisateur appuie sur une touche pour chaque mot.
        # 4. Nécessite une interface plus interactive (ex: avec curses, PySimpleGUI, ou web).
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Synchronise un fichier de paroles (.txt) avec un fichier audio (.mp3) "
                    "pour créer un fichier .lrc."
    )
    parser.add_argument("mp3_path", help="Chemin vers le fichier .mp3")
    parser.add_argument("lyrics_path", help="Chemin vers le fichier .txt des paroles non synchronisées")
    parser.add_argument("-o", "--output", help="Chemin vers le fichier .lrc de sortie (optionnel)")
    parser.add_argument(
        "--mode",
        choices=["line", "word"],
        default="line",
        help="Mode de synchronisation: 'line' (ligne par ligne) ou 'word' (mot par mot, non implémenté)."
    )

    args = parser.parse_args()

    try:
        syncer = LyricsSyncer(args.mp3_path, args.lyrics_path, args.output)

        if args.mode == "line":
            syncer.sync_manually_per_line()
        elif args.mode == "word":
            syncer.sync_manually_per_word()

    except FileNotFoundError as e:
        print(f"Erreur : {e}")
    except Exception as e:
        print(f"Une erreur inattendue est survenue : {e}")

if __name__ == "__main__":
    main()
