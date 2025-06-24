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
    def __init__(self, mp3_path, lyrics_path, output_path=None, output_format="srt"):
        self.mp3_path = mp3_path
        self.lyrics_path = lyrics_path
        self.output_format = output_format # srt ou lrc
        self.output_path = output_path or self._generate_output_path()

        # Le nom de fichier de sortie dépend maintenant du format demandé
        # Si output_path est fourni par l'utilisateur, on respecte son extension.
        # Sinon, on s'assure que l'extension générée correspond à output_format.
        if not output_path: # Si le chemin est auto-généré
            base, _ = os.path.splitext(self.output_path)
            self.output_path = f"{base}.{self.output_format}"
        else: # Si fourni par l'utilisateur, on met à jour output_format basé sur l'extension fournie
            _, ext = os.path.splitext(output_path)
            actual_format = ext.lstrip('.')
            if actual_format in ["lrc", "srt"]:
                self.output_format = actual_format
            # Si l'extension n'est ni lrc ni srt, on garde output_format par défaut et
            # on espère que l'utilisateur sait ce qu'il fait, ou on pourrait lever une erreur.
            # Pour l'instant, on priorise l'extension fournie par l'utilisateur s'il en met une.

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

        try:
            # word_level=True pour avoir des timestamps par mot si possible
            # (stable-ts essaie de produire cela par défaut avec regroup=False)
            self.raw_alignment_result.to_srt_vtt(output_path_srt, word_level=True)
            print(f"✅ Fichier SRT sauvegardé : {output_path_srt}")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde du fichier SRT : {e}")
            return False

    def _convert_stable_ts_result_to_lrc(self):
        """
        Convertit le résultat brut de stable-ts (self.raw_alignment_result)
        en une liste de chaînes au format LRC Enhanced.
        Cette méthode est maintenant un fallback si la conversion SRT->LRC échoue ou n'est pas choisie,
        mais la méthode privilégiée est _convert_srt_content_to_lrc_data.
        """
        # ... (ancienne logique gardée pour référence, mais devrait être dépréciée/supprimée
        #      en faveur de la conversion SRT -> LRC)
        print("Avertissement : _convert_stable_ts_result_to_lrc est appelée, "
              "envisager d'utiliser la conversion SRT->LRC.")
        # Pour l'instant, on retourne une liste vide pour forcer l'utilisation de la nouvelle méthode.
        return []


    def _parse_srt_time(self, srt_time_str):
        """Convertit un timestamp SRT (HH:MM:SS,mmm) en secondes totales (float)."""
        parts = srt_time_str.split(',')
        h_m_s = parts[0].split(':')
        hours = int(h_m_s[0])
        minutes = int(h_m_s[1])
        seconds = int(h_m_s[2])
        milliseconds = int(parts[1])
        total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
        return total_seconds

    def _convert_srt_content_to_lrc_data(self, srt_content_string):
        """
        Convertit une chaîne de contenu SRT (mot par mot) en une liste de chaînes LRC Enhanced.
        """
        lrc_lines = []
        # Regex pour parser un bloc SRT: index, times, text
        # Le texte peut être sur plusieurs lignes, d'où re.DOTALL
        srt_block_pattern = re.compile(
            r"^\d+\s*[\r\n]+"
            r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*[\r\n]+"
            r"(.+?)(?:[\r\n]{2,}|$)",  # Non-capturing group for double newlines or end of string
            re.MULTILINE | re.DOTALL
        )

        # Le SRT généré par stable-ts avec word_level=True a chaque mot comme un bloc SRT.
        # Nous devons regrouper ces mots en lignes basées sur le fichier de paroles original.

        original_line_iter = iter(self.raw_lyrics_lines)
        current_original_line = next(original_line_iter, None)
        current_lrc_line_parts = []
        first_word_timestamp_in_line = -1.0

        for match in srt_block_pattern.finditer(srt_content_string):
            srt_start_time_str, _, srt_word_text = match.groups()
            srt_word_text = srt_word_text.strip() # Nettoyer le texte du mot

            if not srt_word_text: # Skip empty text blocks in SRT if any
                continue

            word_start_sec = self._parse_srt_time(srt_start_time_str)

            if not current_original_line: # Plus de lignes originales à traiter
                print("Avertissement: Plus de mots dans SRT que de lignes originales restantes.")
                break

            if not current_lrc_line_parts: # Début d'une nouvelle ligne LRC
                first_word_timestamp_in_line = word_start_sec
                current_lrc_line_parts.append(f"[{self._format_time(first_word_timestamp_in_line)}]")

            current_lrc_line_parts.append(f"<{self._format_time(word_start_sec)}>{srt_word_text}")

            # Heuristique simple pour savoir quand terminer une ligne LRC:
            # si le mot SRT actuel est le dernier mot de la ligne originale.
            # Cela suppose que la tokenization de stable-ts correspond à .split()
            # ce qui n'est pas toujours vrai, mais c'est un point de départ.
            # Une meilleure approche nécessiterait un alignement plus sophistiqué
            # entre les mots du SRT et les mots des lignes originales.

            # Pour l'instant, on va se baser sur le fait que chaque ligne du SRT est un mot.
            # On essaie de "remplir" la ligne originale.
            if current_original_line.endswith(srt_word_text): # Fin de ligne probable
                lrc_lines.append("".join(current_lrc_line_parts))
                current_lrc_line_parts = []
                first_word_timestamp_in_line = -1.0
                current_original_line = next(original_line_iter, None)
            else:
                # Ajouter un espace si ce n'est pas le premier mot après le timestamp de ligne
                if len(current_lrc_line_parts) > 1 and current_lrc_line_parts[-1] != " ":
                     # L'espace est implicite entre <ts>mot et <ts>mot suivant.
                     pass


        # S'il reste des parties pour une ligne non terminée
        if current_lrc_line_parts:
            lrc_lines.append("".join(current_lrc_line_parts))

        # Correction pour les lignes vides du fichier de paroles original
        # Ceci est une simplification; une correspondance plus robuste serait nécessaire.
        # Pour l'instant, on s'assure de ne pas perdre le "rythme" des lignes vides.
        final_lrc_lines_with_blanks = []
        lrc_iter = iter(lrc_lines)
        for orig_line in self.raw_lyrics_lines:
            if not orig_line.strip():
                final_lrc_lines_with_blanks.append("")
            else:
                try:
                    final_lrc_lines_with_blanks.append(next(lrc_iter))
                except StopIteration:
                    # Plus de contenu LRC généré, mais des lignes originales non vides restantes.
                    # On pourrait les ajouter sans timestamps, ou les ignorer.
                    print(f"Avertissement: Ligne originale '{orig_line}' non couverte par la sortie SRT->LRC.")
                    pass # On les ignore pour l'instant pour éviter des erreurs de format.

        self.synced_lyrics = final_lrc_lines_with_blanks
        if not self.synced_lyrics:
            print("⚠️ Aucune ligne LRC n'a été générée à partir du contenu SRT.")
        return self.synced_lyrics

    def _save_lrc_from_srt_result(self, output_path_lrc):
        """
        Orchestre la génération de SRT par stable-ts, sa conversion en LRC,
        et la sauvegarde du fichier .lrc.
        """
        if not self.raw_alignment_result:
            print("❌ Aucun résultat d'alignement stable-ts à traiter pour générer un LRC via SRT.")
            return False

        # 1. Obtenir le contenu SRT en mémoire
        srt_content_stream = StringIO()
        try:
            self.raw_alignment_result.to_srt_vtt(srt_content_stream, word_level=True)
            srt_content_string = srt_content_stream.getvalue()
            srt_content_stream.close()
        except Exception as e:
            print(f"❌ Erreur lors de la génération du contenu SRT en mémoire : {e}")
            return False

        if not srt_content_string.strip():
            print("❌ Contenu SRT généré par stable-ts est vide.")
            return False

        # 2. Convertir le contenu SRT en données LRC
        lrc_data = self._convert_srt_content_to_lrc_data(srt_content_string)

        # 3. Sauvegarder les données LRC
        if lrc_data: # Si la conversion a produit quelque chose
            # _save_lrc_file utilise self.synced_lyrics qui a été mis à jour
            # par _convert_srt_content_to_lrc_data
            return self._save_lrc_file(output_path_override=output_path_lrc)
        else:
            print("❌ Conversion du SRT en LRC a échoué ou n'a rien produit.")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Synchronise un fichier de paroles (.txt) avec un fichier audio (.mp3) pour créer un fichier .lrc ou .srt.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("mp3_path", help="Chemin vers le fichier .mp3")
    parser.add_argument("lyrics_path", help="Chemin vers le fichier .txt des paroles non synchronisées")
    parser.add_argument("-o", "--output", help="Chemin vers le fichier de sortie (optionnel, défaut: <nom_mp3>.<format>)")

    parser.add_argument(
        "--output_format",
        choices=["lrc", "srt"],
        default="srt",
        help="Format du fichier de sortie pour la synchronisation automatique (défaut: srt)."
    )
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
