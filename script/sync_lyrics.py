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
import stable_whisper # Ajout pour stable-ts
import json # Pour manipuler les résultats de stable-ts si besoin
import re # Pour parser le SRT
from io import StringIO # Pour lire le SRT en mémoire

class LyricsSyncer:
    """
    Classe pour gérer la synchronisation des paroles.
    """
    def __init__(self, mp3_path, lyrics_path, output_path_arg=None, mode="line"):
        self.mp3_path = mp3_path
        self.lyrics_path = lyrics_path
        self.mode = mode
        # self.output_path et self.output_format seront définis par _determine_output_format_and_path
        self.output_path = None
        self.output_format = None

        self._determine_output_format_and_path(output_path_arg)

        if not os.path.exists(self.mp3_path):
            raise FileNotFoundError(f"Fichier MP3 non trouvé : {self.mp3_path}")
        if not os.path.exists(self.lyrics_path):
            raise FileNotFoundError(f"Fichier de paroles non trouvé : {self.lyrics_path}")

        self.raw_lyrics_lines = self._load_raw_lyrics()
        self.synced_lyrics = [] # Contiendra les lignes [mm:ss.xx]Paroles

    def _generate_output_path(self):
        """
        Génère un chemin de sortie par défaut pour le fichier synchronisé,
        en utilisant self.output_format pour déterminer l'extension.
        """
        base, _ = os.path.splitext(self.mp3_path)
        # self.output_format est déjà défini dans __init__ avant l'appel potentiel à cette méthode.
        return f"{base}.{self.output_format}"

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

    def _save_lrc_file(self, output_path_override=None):
        """
        Sauvegarde les paroles synchronisées (contenues dans self.synced_lyrics)
        dans un fichier .lrc.
        Utilise output_path_override si fourni, sinon self.output_path.
        """
        if not self.synced_lyrics:
            print("Aucune parole synchronisée à sauvegarder en LRC.")
            return False # Indiquer l'échec

        # Déterminer le chemin de sauvegarde final
        save_path = output_path_override or self.output_path
        # S'assurer que le chemin final a la bonne extension .lrc si c'est un LRC
        # (normalement géré par __init__ ou par l'appelant pour override)
        # Si output_path_override est fourni, on fait confiance à l'appelant pour l'extension.
        # Si self.output_path est utilisé, il devrait déjà avoir la bonne extension via __init__.

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
        lrc_content.append(f"[by:Autolyrics Syncer v0.1]") # On pourrait ajouter le mode utilisé

        lrc_content.extend(self.synced_lyrics)

        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                for line in lrc_content:
                    f.write(line + "\n")
            print(f"Fichier LRC sauvegardé : {save_path}")
            return True # Indiquer le succès
        except IOError as e:
            print(f"❌ Erreur lors de la sauvegarde du fichier LRC '{save_path}': {e}")
            return False # Indiquer l'échec

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

    def sync_auto_stable_ts(self, model_name="base", language="ja"):
        """
        Synchronise automatiquement les paroles en utilisant stable-ts.
        Le résultat brut de stable-ts est stocké dans self.raw_alignment_result
        pour être traité ultérieurement par une autre méthode pour la conversion LRC.
        """
        print(f"\n🔄 Début de la synchronisation automatique avec stable-ts (modèle: {model_name}, langue: {language})...")
        self.raw_alignment_result = None # Pour stocker le résultat de l'alignement

        if not os.path.exists(self.mp3_path):
            print(f"❌ Erreur : Fichier audio introuvable : {self.mp3_path}")
            return False
        # Le fichier de paroles brutes (self.lyrics_path) est déjà vérifié dans __init__

        print(f"Chargement du modèle Whisper '{model_name}' via stable-ts. Cela peut prendre du temps...")
        try:
            # Forcer CPU pour la cohérence avec l'environnement de test et éviter problèmes GPU AMD
            model = stable_whisper.load_model(model_name, device="cpu")
            print("Modèle chargé.")
        except Exception as e:
            print(f"❌ Erreur lors du chargement du modèle Whisper '{model_name}': {e}")
            return False

        print(f"Lecture du fichier texte des paroles : {self.lyrics_path}")
        with open(self.lyrics_path, 'r', encoding='utf-8') as f:
            text_content = f.read()

        if not text_content.strip():
            print("❌ Erreur : Le fichier texte des paroles est vide.")
            return False

        print(f"Alignement de '{self.mp3_path}' avec le texte fourni...")
        start_process_time = time.time()

        try:
            # Utilisation de model.align()
            # regroup=False est crucial pour obtenir des timestamps au niveau du mot/segment fin.
            result = model.align(self.mp3_path, text_content, language=language, regroup=False)
            self.raw_alignment_result = result

        except Exception as e:
            print(f"❌ Erreur lors de l'alignement avec stable-ts : {e}")
            return False

        end_process_time = time.time()
        print(f"✅ Alignement par stable-ts terminé en {end_process_time - start_process_time:.2f} secondes.")

        # À ce stade, self.raw_alignment_result contient l'objet WhisperResult.
        # La conversion en LRC sera faite dans une étape/méthode séparée.
        # Pour l'instant, on peut afficher un résumé ou un indicateur de succès.

        if self.raw_alignment_result and hasattr(self.raw_alignment_result, 'segments'):
            print(f"Nombre de segments alignés : {len(self.raw_alignment_result.segments)}")
            # Sauvegarde temporaire du JSON pour inspection si besoin (peut être retiré plus tard)
            temp_json_path = os.path.splitext(self.output_path)[0] + "_stable_ts_debug.json"
            try:
                with open(temp_json_path, 'w', encoding='utf-8') as f_json:
                    json.dump(self.raw_alignment_result.to_dict(), f_json, indent=2, ensure_ascii=False)
                print(f"Résultat brut de l'alignement sauvegardé (pour debug) : {temp_json_path}")
            except Exception as e_json:
                print(f"Avertissement : Impossible de sauvegarder le JSON de debug : {e_json}")
            return True
        else:
            print("⚠️ Aucun segment n'a été retourné par stable-ts.")
            return False

    def _save_stable_ts_result_as_srt(self, output_path_srt):
        """
        Sauvegarde le résultat de l'alignement stable-ts directement en format SRT.
        """
        if not self.raw_alignment_result:
            print("❌ Aucun résultat d'alignement stable-ts à sauvegarder en SRT.")
            return False

        # S'assurer que le chemin de sortie a bien l'extension .srt
        # Normalement déjà géré par _determine_output_format_and_path si mode='auto_stablets'
        # et aucun output_path_arg n'a été fourni avec une autre extension.
        # Mais on peut forcer ici pour être sûr si cette méthode est appelée directement.
        base, _ = os.path.splitext(output_path_srt)
        actual_output_path_srt = f"{base}.srt"

        try:
            self.raw_alignment_result.to_srt_vtt(actual_output_path_srt, word_level=True)
            print(f"✅ Fichier SRT sauvegardé : {actual_output_path_srt}")
            # Mettre à jour self.output_path au cas où l'extension aurait été forcée ici
            self.output_path = actual_output_path_srt
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde du fichier SRT : {e}")
            return False

    # Les méthodes _convert_stable_ts_result_to_lrc, _parse_srt_time,
    # _convert_srt_content_to_lrc_data, et _save_lrc_from_srt_result sont supprimées.

def main():
    parser = argparse.ArgumentParser(
        description="Synchronise un fichier de paroles (.txt) avec un fichier audio (.mp3).\n"
                    "Mode manuel ('line') produit un .lrc.\n"
                    "Mode automatique ('auto_stablets') produit un .srt.",
        formatter_class=argparse.RawTextHelpFormatter # Pour mieux contrôler le help multiligne
    )
    parser.add_argument("mp3_path", help="Chemin vers le fichier .mp3")
    parser.add_argument("lyrics_path", help="Chemin vers le fichier .txt des paroles non synchronisées")
    parser.add_argument("-o", "--output", help="Chemin vers le fichier de sortie (optionnel, défaut: <nom_mp3>.[lrc|srt])")

    # L'option --output_format est supprimée. Le format est déterminé par le mode.

    parser.add_argument(
        "--mode",
        choices=["line", "auto_stablets"], # "word" (manuel mot/mot) n'est pas implémenté
        default="line",
        help=("Mode de synchronisation:\n"
              "  'line': Manuel, ligne par ligne.\n"
              "  'word': Manuel, mot par mot (non implémenté).\n"
              "  'auto_stablets': Automatique avec stable-ts (Whisper).")
    )
    # Options spécifiques pour auto_stablets
    parser.add_argument(
        "--st_model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large", "large-v1", "large-v2", "large-v3"],
        help="Modèle Whisper à utiliser pour le mode 'auto_stablets'."
    )
    parser.add_argument(
        "--st_lang",
        default="ja",
        help="Code langue pour Whisper en mode 'auto_stablets' (ex: 'ja', 'en')."
    )

    args = parser.parse_args()

    try:
        syncer = LyricsSyncer(args.mp3_path, args.lyrics_path, args.output, args.output_format)

        if args.mode == "line":
            # Le mode manuel génère toujours du LRC pour l'instant.
            # Si l'output_format demandé est SRT, on pourrait afficher un avertissement
            # ou désactiver la sauvegarde si on veut être strict.
            # Pour l'instant, il sauvegardera en .lrc (car self.output_path est ajusté dans __init__)
            # si output_path n'est pas spécifié, ou avec l'extension donnée par l'utilisateur.
            if syncer.output_format == "srt":
                print("Avertissement : Le mode de synchronisation manuel 'line' génère du .lrc. "
                      "L'option --output_format=srt est ignorée pour ce mode, sauf si "
                      "le nom de fichier de sortie explicite se termine par .srt.")
            syncer.sync_manually_per_line()
        elif args.mode == "word":
            syncer.sync_manually_per_word() # Toujours non implémenté
        elif args.mode == "auto_stablets":
            align_success = syncer.sync_auto_stable_ts(model_name=args.st_model, language=args.st_lang)
            if align_success:
                if syncer.output_format == "srt":
                    print(f"Génération du fichier SRT (chemin: {syncer.output_path})...")
                    save_success = syncer._save_stable_ts_result_as_srt(syncer.output_path)
                    if save_success:
                        print("✅ Fichier SRT généré avec succès.")
                    else:
                        print("❌ Échec de la sauvegarde du fichier SRT.")
                elif syncer.output_format == "lrc":
                    print(f"Génération du fichier LRC via conversion SRT (chemin: {syncer.output_path})...")
                    save_success = syncer._save_lrc_from_srt_result(syncer.output_path)
                    if save_success:
                        print("✅ Fichier LRC généré avec succès via conversion SRT.")
                    else:
                        print("❌ Échec de la génération du fichier LRC via conversion SRT.")
                else:
                    # Normalement, __init__ force output_format à srt ou lrc si un chemin de sortie est donné
                    # ou si le format par défaut est utilisé. Ce cas ne devrait pas arriver.
                    print(f"Format de sortie non supporté '{syncer.output_format}' pour le mode auto_stablets.")
            else:
                print("❌ La synchronisation automatique avec stable-ts a échoué. Aucun fichier ne sera généré.")

    except FileNotFoundError as e:
        print(f"Erreur : {e}")
    except Exception as e:
        print(f"Une erreur inattendue est survenue : {e}")

if __name__ == "__main__":
    main()
