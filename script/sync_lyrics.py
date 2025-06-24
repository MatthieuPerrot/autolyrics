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

    def _convert_stable_ts_result_to_lrc(self):
        """
        Convertit le résultat brut de stable-ts (self.raw_alignment_result)
        en une liste de chaînes au format LRC Enhanced.
        Chaque ligne originale du fichier de paroles est reconstituée avec
        des timestamps pour la ligne et pour chaque mot.
        """
        if not self.raw_alignment_result or not hasattr(self.raw_alignment_result, 'segments'):
            print("Aucun résultat d'alignement stable-ts à convertir.")
            return []

        lrc_lines = []

        # self.raw_lyrics_lines contient les lignes originales du fichier .txt
        # self.raw_alignment_result contient les mots reconnus et alignés par Whisper/stable-ts.
        # La fonction `align` de stable-ts devrait avoir aligné les mots de notre texte original.

        # On itère sur les segments du résultat de l'alignement.
        # Chaque segment peut correspondre à une ou plusieurs lignes du texte original,
        # ou à une partie d'une ligne, selon la segmentation de stable-ts.
        # Cependant, avec regroup=False, on s'attend à des segments assez fins.

        # L'objet WhisperResult de stable-ts (après .align()) a une structure pratique:
        # result.lines est une liste de dictionnaires, où chaque dictionnaire représente une ligne
        # du texte original et contient une clé 'words' avec les mots alignés pour cette ligne.
        # Ou, plus directement, result.segments contient des mots qui ont un word.line_idx
        # et word.line_word_idx si `word_timestamps=True` (défaut) et `regroup=False`.

        # On va itérer sur les lignes originales pour reconstruire la structure LRC.
        # Et pour chaque ligne, on va chercher les mots correspondants dans le résultat de stable-ts.

        current_word_index_in_result = 0
        all_aligned_words = []
        for segment in self.raw_alignment_result.segments:
            all_aligned_words.extend(segment.words)

        # Si le texte original a été fourni à `align`, les mots dans `all_aligned_words`
        # devraient correspondre séquentiellement aux mots du texte original.
        # On va essayer de mapper cela aux lignes originales.

        word_iterator = iter(all_aligned_words)

        for original_line_text in self.raw_lyrics_lines:
            if not original_line_text.strip(): # Gérer les lignes vides du fichier original
                lrc_lines.append("") # Ajouter une ligne vide dans le LRC
                continue

            original_words_in_line = original_line_text.split()
            if not original_words_in_line: # Ligne originale avec juste des espaces
                lrc_lines.append("")
                continue

            line_lrc_parts = []
            line_start_time_sec = -1

            for i, expected_word_original in enumerate(original_words_in_line):
                try:
                    # On consomme les mots de stable-ts.
                    # On s'attend à ce que le texte du mot de stable-ts corresponde (plus ou moins)
                    # au mot original. stable-ts.align devrait garantir cela.
                    aligned_word_obj = next(word_iterator)

                    # Le texte de `aligned_word_obj.word` peut avoir une casse différente ou des ponctuations nettoyées.
                    # On utilise le texte original `expected_word_original` pour la sortie LRC.
                    # Le timestamp vient de `aligned_word_obj`.

                    word_start_time_sec = aligned_word_obj.start

                    if i == 0: # Premier mot de la ligne
                        line_start_time_sec = word_start_time_sec
                        line_lrc_parts.append(f"[{self._format_time(line_start_time_sec)}]")

                    # Timestamp du mot
                    line_lrc_parts.append(f"<{self._format_time(word_start_time_sec)}>{expected_word_original}")

                except StopIteration:
                    # Plus de mots alignés par stable-ts, mais il reste des mots dans la ligne originale.
                    # Cela peut arriver si la fin de l'audio est atteinte ou si l'alignement est partiel.
                    print(f"⚠️ Avertissement : Moins de mots alignés par stable-ts que dans la ligne originale : '{original_line_text}'")
                    # On ajoute les mots restants sans timestamp de mot spécifique, ou on arrête.
                    # Pour l'instant, on s'arrête pour cette ligne pour éviter des LRC mal formés.
                    if not line_lrc_parts or not line_lrc_parts[0].startswith("["): # Si on n'a même pas eu le timestamp de ligne
                        line_lrc_parts = [f"[{self._format_time(0.0)}]"+original_line_text] # Fallback grossier
                    break
                except Exception as e:
                    print(f"Erreur en traitant un mot aligné : {e}")
                    # Essayer de continuer avec le mot suivant, ou ajouter le mot original sans timestamp
                    line_lrc_parts.append(expected_word_original)


            if line_lrc_parts:
                lrc_lines.append("".join(line_lrc_parts))
            elif original_line_text.strip(): # Si la ligne originale n'était pas vide mais rien n'a été produit
                print(f"Avertissement : La ligne '{original_line_text}' n'a pas pu être convertie en LRC.")
                # Fallback : ajouter la ligne avec un timestamp de 0 ou le dernier timestamp connu ?
                # Pour l'instant, on l'omet pour éviter des erreurs.
                # Ou on l'ajoute sans timestamp de mot :
                # lrc_lines.append(f"[{self._format_time(line_start_time_sec if line_start_time_sec != -1 else 0.0)}]{original_line_text}")


        self.synced_lyrics = lrc_lines # Stocker pour _save_lrc_file
        if not lrc_lines:
            print("⚠️ Aucune ligne LRC n'a été générée à partir du résultat de stable-ts.")
        return lrc_lines


def main():
    parser = argparse.ArgumentParser(
        description="Synchronise un fichier de paroles (.txt) avec un fichier audio (.mp3) pour créer un fichier .lrc.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("mp3_path", help="Chemin vers le fichier .mp3")
    parser.add_argument("lyrics_path", help="Chemin vers le fichier .txt des paroles non synchronisées")
    parser.add_argument("-o", "--output", help="Chemin vers le fichier .lrc de sortie (optionnel, défaut: <nom_mp3>.lrc)")

    parser.add_argument(
        "--mode",
        choices=["line", "word", "auto_stablets"],
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
        syncer = LyricsSyncer(args.mp3_path, args.lyrics_path, args.output)

        if args.mode == "line":
            syncer.sync_manually_per_line()
        elif args.mode == "word":
            syncer.sync_manually_per_word() # Toujours non implémenté
        elif args.mode == "auto_stablets":
            success_align = syncer.sync_auto_stable_ts(model_name=args.st_model, language=args.st_lang)
            if success_align:
                lrc_content = syncer._convert_stable_ts_result_to_lrc()
                if lrc_content: # Si la conversion a produit quelque chose
                    syncer._save_lrc_file() # _save_lrc_file utilise self.synced_lyrics qui a été mis à jour
                else:
                    print("❌ Conversion du résultat de stable-ts en LRC a échoué ou n'a rien produit.")
            else:
                print("❌ La synchronisation automatique avec stable-ts a échoué.")

    except FileNotFoundError as e:
        print(f"Erreur : {e}")
    except Exception as e:
        print(f"Une erreur inattendue est survenue : {e}")

if __name__ == "__main__":
    main()
