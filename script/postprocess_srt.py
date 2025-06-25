#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour post-traiter un fichier SRT détaillé (généré par stable-ts,
avec texte complet et surbrillance progressive) afin de produire différents
modes d'affichage pour le karaoké.
"""

import argparse
import os
import re

# Regex pour parser un bloc SRT standard
SRT_BLOCK_PATTERN = re.compile(
    r"(\d+)\s*[\r\n]+"  # 1: Index
    r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*[\r\n]+"  # 2 & 3: Start & End timestamps
    r"((?:.+\s*[\r\n]*)+)",  # 4: Text (peut être sur plusieurs lignes)
    re.MULTILINE
)

# Regex pour trouver le segment en surbrillance (ex: <font color="#00ff00">mot</font>)
# et capturer le texte avant, le texte en surbrillance, et le texte après.
HIGHLIGHT_PATTERN = re.compile(r"(.*?)<font color=\"[^\"]+\">(.*?)</font>(.*)", re.DOTALL)

def clean_text_for_offset_calculation(text_segment):
    """Nettoie un segment de texte de ses balises <font> pour calculer la longueur."""
    return re.sub(r"<font[^>]*>|<\/font>", "", text_segment)

def find_line_index_from_offset(original_lines_stripped, target_offset):
    """
    Trouve l'index de la ligne dans original_lines_stripped (liste de lignes nettoyées)
    qui contient le caractère à target_offset (0-indexé) dans le texte concaténé de ces lignes.
    Les sauts de ligne entre les lignes originales sont comptés comme 1 caractère.
    """
    current_char_pos = 0
    for i, line_text in enumerate(original_lines_stripped):
        line_len = len(line_text)
        # L'offset cible est-il dans cette ligne ?
        # (current_char_pos <= target_offset < current_char_pos + line_len)
        if target_offset < current_char_pos + line_len:
            return i
        # L'offset cible est-il sur le "newline" qui suit cette ligne ?
        # Dans ce cas, il appartient à la ligne suivante.
        if target_offset == current_char_pos + line_len and i < len(original_lines_stripped) - 1:
            return i + 1

        current_char_pos += line_len
        if i < len(original_lines_stripped) - 1: # S'il y a une ligne suivante
            current_char_pos += 1 # Compter 1 pour le saut de ligne implicite

    # Si l'offset est égal ou supérieur à la position de fin du dernier caractère de la dernière ligne
    if target_offset >= current_char_pos:
        return len(original_lines_stripped) - 1

    return -1 # Non trouvé

def parse_srt_file(srt_filepath):
    if not os.path.exists(srt_filepath):
        raise FileNotFoundError(f"Fichier SRT d'entrée introuvable : {srt_filepath}")
    with open(srt_filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    blocks = []
    for match in SRT_BLOCK_PATTERN.finditer(content):
        blocks.append({
            "index": int(match.group(1)),
            "start_time": match.group(2),
            "end_time": match.group(3),
            "text_with_highlight": match.group(4).strip()
        })
    return blocks

def load_original_lyrics(lyrics_filepath):
    if not os.path.exists(lyrics_filepath):
        raise FileNotFoundError(f"Fichier de paroles originales introuvable : {lyrics_filepath}")
    with open(lyrics_filepath, 'r', encoding='utf-8') as f:
        # On garde les lignes telles quelles, le strip sera fait au besoin
        lines = [line.rstrip('\r\n') for line in f]
    return lines

def postprocess_srt(input_srt_path, original_lyrics_path, output_srt_path, display_mode):
    srt_blocks = parse_srt_file(input_srt_path)
    original_lines = load_original_lyrics(original_lyrics_path)
    # Version nettoyée des lignes originales pour le calcul d'offset et la recherche
    original_lines_stripped_for_logic = [line.strip() for line in original_lines]

    output_srt_content = []
    new_block_index = 1

    if not srt_blocks:
        print("Aucun bloc trouvé dans le fichier SRT d'entrée.")
        # Écrire un fichier vide ou un message ? Pour l'instant, fichier vide.
        with open(output_srt_path, 'w', encoding='utf-8') as f:
            f.write("")
        print(f"Fichier SRT de sortie vide créé : {output_srt_path}")
        return

    if display_mode == "word":
        for block in srt_blocks:
            match_highlight = HIGHLIGHT_PATTERN.match(block["text_with_highlight"])
            if match_highlight:
                _, highlighted_text, _ = match_highlight.groups()
                if highlighted_text.strip():
                    output_srt_content.append(f"{new_block_index}\n"
                                             f"{block['start_time']} --> {block['end_time']}\n"
                                             f"{highlighted_text.strip()}\n")
                    new_block_index += 1
            else: # Pas de surbrillance, on copie le bloc original
                output_srt_content.append(f"{new_block_index}\n"
                                     f"{block['start_time']} --> {block['end_time']}\n"
                                     f"{block['text_with_highlight'].strip()}\n")
                new_block_index += 1

    elif display_mode in ["line", "line_plus_next"]:
        # Précalculer les offsets de début de chaque ligne originale (nettoyée)
        # dans le contexte du texte global nettoyé.
        original_line_global_start_offsets = [0] * len(original_lines_stripped_for_logic)
        current_global_char_pos = 0
        for i, line_s in enumerate(original_lines_stripped_for_logic):
            original_line_global_start_offsets[i] = current_global_char_pos
            current_global_char_pos += len(line_s)
            if i < len(original_lines_stripped_for_logic) - 1:
                current_global_char_pos += 1 # Pour le saut de ligne

        for block in srt_blocks:
            match_highlight = HIGHLIGHT_PATTERN.match(block["text_with_highlight"])
            if not match_highlight:
                output_srt_content.append(f"{new_block_index}\n"
                                         f"{block['start_time']} --> {block['end_time']}\n"
                                         f"{block['text_with_highlight'].strip()}\n")
                new_block_index += 1
                continue

            text_before_font, highlighted_segment_with_font, text_after_font = match_highlight.groups()

            clean_text_before_font = clean_text_for_offset_calculation(text_before_font)
            start_offset_of_highlight_in_global_clean_text = len(clean_text_before_font)

            line_idx = find_line_index_from_offset(original_lines_stripped_for_logic, start_offset_of_highlight_in_global_clean_text)

            if line_idx != -1:
                # Ligne originale (non strippée au départ, pour garder les espaces voulus)
                current_original_line_display = original_lines[line_idx]
                clean_highlighted_segment = clean_text_for_offset_calculation(highlighted_segment_with_font)

                # Calculer l'offset relatif du segment surligné à l'intérieur de sa ligne originale (strippée)
                relative_start_offset_in_line = start_offset_of_highlight_in_global_clean_text - original_line_global_start_offsets[line_idx]

                # S'assurer que l'offset relatif est plausible et que le segment est inclus
                line_for_replacement = original_lines_stripped_for_logic[line_idx]

                if (0 <= relative_start_offset_in_line and
                    relative_start_offset_in_line + len(clean_highlighted_segment) <= len(line_for_replacement)):

                    # Vérifier si le segment propre correspond bien à ce qu'il y a dans la ligne originale à cet offset
                    extracted_from_original = line_for_replacement[relative_start_offset_in_line : relative_start_offset_in_line + len(clean_highlighted_segment)]
                    if clean_text_for_offset_calculation(extracted_from_original.lower()) == clean_text_for_offset_calculation(clean_highlighted_segment.lower()):
                        # Reconstruction: on prend la ligne originale (avec ses espaces de début/fin potentiels)
                        # et on essaie d'y insérer le highlighted_segment_with_font.
                        # Pour cela, on a besoin des vrais offsets sur la ligne originale non-strippée.
                        # C'est ici que ça devient complexe si la ligne originale a des espaces significatifs
                        # au début/fin qui ont été enlevés par .strip() pour le calcul d'offset.

                        # Solution plus simple: on travaille avec la ligne originale strippée pour la reconstruction
                        # et on la `.strip()` à la fin pour l'affichage SRT.
                        line_part_before = line_for_replacement[:relative_start_offset_in_line]
                        line_part_after = line_for_replacement[relative_start_offset_in_line + len(clean_highlighted_segment):]

                        output_text_for_block = line_part_before + highlighted_segment_with_font + line_part_after
                    else:
                        print(f"Avertissement: Discordance de segment pour remplacement bloc {block['index']}. "
                              f"Ligne: '{line_for_replacement}', Attendu: '{clean_highlighted_segment}', Trouvé: '{extracted_from_original}'. "
                              f"Utilisation de la ligne originale '{original_lines[line_idx].strip()}' avec surbrillance approximative.")
                        # Fallback: remplacer la première occurrence dans la ligne strippée (moins précis)
                        output_text_for_block = original_lines[line_idx].strip().replace(clean_highlighted_segment, highlighted_segment_with_font, 1)
                else:
                    print(f"Avertissement: Offset relatif ({relative_start_offset_in_line}) ou longueur du segment "
                          f"hors limites pour la ligne {line_idx}: '{line_for_replacement}'. "
                          f"Segment: '{clean_highlighted_segment}'. Bloc SRT {block['index']} utilise la ligne originale brute.")
                    output_text_for_block = original_lines[line_idx].strip() # Ligne originale sans surbrillance spécifique

                if display_mode == "line_plus_next":
                    if line_idx + 1 < len(original_lines):
                        output_text_for_block += "\n" + original_lines[line_idx + 1].strip()

                output_srt_content.append(f"{new_block_index}\n"
                                         f"{block['start_time']} --> {block['end_time']}\n"
                                         f"{output_text_for_block.strip()}\n")
                new_block_index += 1
            else:
                print(f"Avertissement: Impossible de localiser la ligne originale pour le bloc {block['index']}. Bloc copié tel quel.")
                output_srt_content.append(f"{new_block_index}\n"
                                         f"{block['start_time']} --> {block['end_time']}\n"
                                         f"{block['text_with_highlight'].strip()}\n")
                new_block_index += 1
    else: # Should not happen due to argparse choices
        print(f"Mode d'affichage inconnu : {display_mode}")
        return


    with open(output_srt_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(output_srt_content))
        # Assurer une newline à la fin si le contenu n'est pas vide
        if output_srt_content:
            f.write("\n")

    print(f"Fichier SRT post-traité sauvegardé : {output_srt_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Post-traite un fichier SRT détaillé pour différents modes d'affichage karaoké.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_srt_file", help="Chemin vers le fichier .srt d'entrée (détaillé, mot/syllabe en surbrillance).")
    parser.add_argument("original_lyrics_file", help="Chemin vers le fichier .txt des paroles originales (pour structure des lignes).")
    parser.add_argument("output_srt_file", help="Chemin vers le fichier .srt de sortie (post-traité).")

    parser.add_argument(
        "--display_mode",
        choices=["word", "line", "line_plus_next"],
        default="word",
        help=(
            "Mode d'affichage à générer:\n"
            "  'word': (Défaut) Chaque segment du SRT d'entrée devient une entrée SRT contenant uniquement le mot/segment en surbrillance.\n"
            "  'line': Chaque entrée SRT affichera la ligne de paroles originale complète où se trouve le mot/segment en surbrillance, avec ce dernier conservant sa surbrillance.\n"
            "  'line_plus_next': Comme 'line', mais affiche aussi la ligne de paroles originale suivante."
        )
    )
    args = parser.parse_args()

    try:
        postprocess_srt(args.input_srt_file, args.original_lyrics_file, args.output_srt_file, args.display_mode)
    except FileNotFoundError as e:
        print(f"Erreur : {e}")
    except Exception as e:
        print(f"Une erreur inattendue est survenue : {e}")

if __name__ == "__main__":
    main()
