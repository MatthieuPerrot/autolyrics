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
    # 4: Text (peut être sur plusieurs lignes), suivi par ligne vide ou fin de chaîne (non-capturant)
    r"((?:.+[\r\n])+)(?:^\s*[\r\n]|$)",  # 4: Text (peut être sur plusieurs lignes), suivi par ligne vide ou fin de chaîne
    re.MULTILINE
)

# Regex pour trouver le segment en surbrillance (ex: <font color="#00ff00">mot</font>)
# et capturer le texte avant, le texte en surbrillance, et le texte après.
HIGHLIGHT_PATTERN = re.compile(r"(.*?)(<font color=\"[^\"]+\">.*?</font>)(.*)", re.DOTALL)

def clean_text_remove_font_tags(text_segment):
    """Nettoie un segment de texte de ses balises <font>."""
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
        if target_offset < current_char_pos + line_len:
            return i
        if target_offset == current_char_pos + line_len and i < len(original_lines_stripped) - 1:
            return i + 1
        current_char_pos += line_len
        if i < len(original_lines_stripped) - 1:
            current_char_pos += 1
    if target_offset >= current_char_pos:
        if original_lines_stripped:
            return len(original_lines_stripped) - 1
        else:
            return -1
    return -1

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
        lines = [line.rstrip('\r\n') for line in f]
    return lines

def postprocess_srt(input_srt_path, original_lyrics_path, output_srt_path, display_mode, highlight_style):
    srt_blocks = parse_srt_file(input_srt_path)
    original_lines = load_original_lyrics(original_lyrics_path)
    original_lines_stripped_for_logic = [line.strip() for line in original_lines]

    output_srt_content_parts = []
    new_block_index = 1

    if not srt_blocks:
        # Gérer le cas où srt_blocks est vide
        with open(output_srt_path, 'w', encoding='utf-8') as f:
            f.write("")
        print(f"Fichier SRT d'entrée vide ou non parsable. Fichier de sortie vide créé : {output_srt_path}")
        return

    if display_mode == "word":
        for block in srt_blocks:
            match_highlight = HIGHLIGHT_PATTERN.match(block["text_with_highlight"])
            if match_highlight:
                _, highlighted_text_with_font, _ = match_highlight.groups()
                if highlighted_text_with_font.strip():
                    final_text_for_block = highlighted_text_with_font.strip()
                    if highlight_style == "none":
                        final_text_for_block = clean_text_remove_font_tags(final_text_for_block)
                    elif highlight_style == "line_all": # Pour 'word', 'line_all' surligne juste le mot lui-même
                        cleaned_word = clean_text_remove_font_tags(final_text_for_block)
                        final_text_for_block = f"<font color=\"#00ff00\">{cleaned_word}</font>"

                    output_srt_content_parts.append(f"{new_block_index}\n"
                                             f"{block['start_time']} --> {block['end_time']}\n"
                                             f"{final_text_for_block}")
                    new_block_index += 1
            else: # Pas de surbrillance == pas de paroles significatives à isoler pour ce mode
                pass # On ignore ce bloc

    elif display_mode in ["line", "line_plus_next"]:
        original_line_global_start_offsets = [0] * len(original_lines_stripped_for_logic)
        current_global_char_pos = 0
        for i, line_s in enumerate(original_lines_stripped_for_logic):
            original_line_global_start_offsets[i] = current_global_char_pos
            current_global_char_pos += len(line_s)
            if i < len(original_lines_stripped_for_logic) - 1:
                current_global_char_pos += 1

        for block in srt_blocks:
            match_highlight = HIGHLIGHT_PATTERN.match(block["text_with_highlight"])
            if not match_highlight:
                continue

            text_before_font, highlighted_segment_with_font, text_after_font = match_highlight.groups()
            clean_text_before_font = clean_text_remove_font_tags(text_before_font)
            start_offset_of_highlight_in_global_clean_text = len(clean_text_before_font)

            line_idx = find_line_index_from_offset(original_lines_stripped_for_logic, start_offset_of_highlight_in_global_clean_text)

            reconstructed_line_with_preserved_highlight = ""

            if line_idx != -1:
                target_original_line_display = original_lines[line_idx] # Ligne originale avec potentiels espaces
                line_for_replacement_logic = original_lines_stripped_for_logic[line_idx]
                clean_highlighted_segment = clean_text_remove_font_tags(highlighted_segment_with_font)

                relative_start_offset_in_line = start_offset_of_highlight_in_global_clean_text - original_line_global_start_offsets[line_idx]

                if (0 <= relative_start_offset_in_line and
                        relative_start_offset_in_line + len(clean_highlighted_segment) <= len(line_for_replacement_logic)):
                    extracted_from_original_at_offset = line_for_replacement_logic[
                        relative_start_offset_in_line : relative_start_offset_in_line + len(clean_highlighted_segment)
                    ]
                    norm_extracted = ' '.join(extracted_from_original_at_offset.lower().split())
                    norm_clean_highlight = ' '.join(clean_highlighted_segment.lower().split())

                    if norm_extracted == norm_clean_highlight:
                        prefix = line_for_replacement_logic[:relative_start_offset_in_line]
                        suffix = line_for_replacement_logic[relative_start_offset_in_line + len(clean_highlighted_segment):]
                        reconstructed_line_with_preserved_highlight = prefix + highlighted_segment_with_font + suffix
                    else:
                        # Fallback: Remplacement simple insensible à la casse sur la ligne strippée
                        pattern_to_replace = re.compile(re.escape(clean_highlighted_segment), re.IGNORECASE)
                        temp_replaced_line = pattern_to_replace.sub(highlighted_segment_with_font, line_for_replacement_logic, 1)
                        if temp_replaced_line != line_for_replacement_logic : # Si le remplacement a eu lieu
                           reconstructed_line_with_preserved_highlight = temp_replaced_line
                        else: # Remplacement a échoué, on prend la ligne originale sans surbrillance spécifique
                           reconstructed_line_with_preserved_highlight = line_for_replacement_logic
                           print(f"Avertissement: Impossible de remplacer '{clean_highlighted_segment}' dans la ligne {line_idx} pour le bloc {block['index']}.")
                else:
                    reconstructed_line_with_preserved_highlight = line_for_replacement_logic
                    print(f"Avertissement: Offset relatif invalide pour surbrillance dans bloc {block['index']}.")
            else: # line_idx == -1
                print(f"Avertissement: Impossible de localiser la ligne originale pour le bloc {block['index']}. Utilisation du texte du bloc SRT original.")
                reconstructed_line_with_preserved_highlight = block["text_with_highlight"] # Texte complet du bloc SRT

            # Application du style de surbrillance final
            final_text_for_block = ""
            if highlight_style == "preserve":
                final_text_for_block = reconstructed_line_with_preserved_highlight
            elif highlight_style == "none":
                final_text_for_block = clean_text_remove_font_tags(reconstructed_line_with_preserved_highlight)
            elif highlight_style == "line_all":
                cleaned_text = clean_text_remove_font_tags(reconstructed_line_with_preserved_highlight)
                final_text_for_block = f"<font color=\"#00ff00\">{cleaned_text}</font>"

            if display_mode == "line_plus_next":
                if line_idx != -1 and line_idx + 1 < len(original_lines):
                    # Pour la ligne suivante, on la prend telle quelle, sans surbrillance de style 'line_all'
                    # sauf si on change cette logique. Pour 'none', elle sera propre.
                    next_line_text = original_lines[line_idx + 1].strip()
                    if highlight_style == "line_all": # Surligner aussi la ligne suivante
                         final_text_for_block += f"\n<font color=\"#00ff00\">{next_line_text}</font>"
                    elif highlight_style == "none":
                         final_text_for_block += "\n" + next_line_text # Déjà propre
                    # Pas de 'else', car si c'est 'preserve', la ligne suivante n'a pas de surbrillance à préserver intrinsèquement
                    # elle est juste ajoutée. La coloration grise est déjà appliquée si highlight_style == 'preserve'.


            output_srt_content_parts.append(f"{new_block_index}\n"
                                         f"{block['start_time']} --> {block['end_time']}\n"
                                         f"{final_text_for_block.strip()}")
            new_block_index += 1
    else:
        print(f"Mode d'affichage inconnu : {display_mode}. Le fichier de sortie sera une copie de l'entrée.")
        for block in srt_blocks: # Fallback pour copier l'entrée si mode inconnu
             output_srt_content_parts.append(f"{new_block_index}\n"
                                     f"{block['start_time']} --> {block['end_time']}\n"
                                     f"{block['text_with_highlight'].strip()}")
             new_block_index += 1

    with open(output_srt_path, 'w', encoding='utf-8') as f:
        f.write("\n\n".join(output_srt_content_parts))
        if output_srt_content_parts and not output_srt_content_parts[-1].endswith('\n\n'):
             f.write("\n") # Assurer un double saut de ligne final si nécessaire pour certains lecteurs

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
            "  'line': Affiche la ligne de paroles originale complète où se trouve le mot/segment en surbrillance.\n"
            "  'line_plus_next': Comme 'line', mais affiche aussi la ligne de paroles originale suivante."
        )
    )
    parser.add_argument(
        "--highlight_style",
        choices=["preserve", "line_all", "none"],
        default="preserve",
        help=(
            "Style de surbrillance à appliquer (principalement pour les modes 'line' et 'line_plus_next'):\n"
            "  'preserve': (Défaut) Conserve la surbrillance du mot/segment d'origine.\n"
            "  'line_all': Met en surbrillance toute la ligne courante (et la suivante si applicable).\n"
            "  'none': Aucune surbrillance, affiche le texte brut des lignes."
        )
    )
    args = parser.parse_args()

    try:
        postprocess_srt(args.input_srt_file, args.original_lyrics_file, args.output_srt_file, args.display_mode, args.highlight_style)
    except FileNotFoundError as e:
        print(f"Erreur : {e}")
    except Exception as e:
        print(f"Une erreur inattendue est survenue : {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
