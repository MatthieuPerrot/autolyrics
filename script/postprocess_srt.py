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

def parse_srt_file(srt_filepath):
    """
    Parse un fichier SRT et retourne une liste de blocs.
    Chaque bloc est un dictionnaire avec 'index', 'start_time', 'end_time', 'text'.
    Le texte contient les balises de surbrillance.
    """
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
    """Charge les lignes de paroles depuis le fichier .txt original."""
    if not os.path.exists(lyrics_filepath):
        raise FileNotFoundError(f"Fichier de paroles originales introuvable : {lyrics_filepath}")
    with open(lyrics_filepath, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f] # Garder les lignes vides pour la structure
    return lines

def find_line_index_for_highlighted_text(original_lines, highlighted_text_segment, text_before_highlight, text_after_highlight):
    """
    Tente de trouver l'index de la ligne dans original_lines qui contient le segment en surbrillance.
    Cette fonction est cruciale et peut être complexe à rendre robuste.
    """
    # Normaliser le texte pour la recherche (enlever les espaces multiples, etc.)
    # Le texte dans le SRT (avant/highlight/après) est l'intégralité des paroles.
    # On cherche la position du highlighted_text_segment dans ce texte complet.

    full_text_from_srt_block = text_before_highlight + highlighted_text_segment + text_after_highlight
    # Nettoyer le texte complet des balises pour le comparer aux lignes originales
    clean_full_text_from_srt = re.sub(r'<[^>]+>', '', full_text_from_srt_block).replace('\r', '')

    # Concaténer les lignes originales pour avoir une référence
    # en gardant une trace des débuts/fins de ligne.
    # On doit trouver où se situe `highlighted_text_segment` par rapport aux lignes originales.

    # Approche simplifiée pour l'instant:
    # On suppose que `highlighted_text_segment` est unique ou que sa première occurrence est la bonne.
    # On nettoie aussi le segment en surbrillance de ses propres balises si on compare avec du texte propre.
    clean_highlight = re.sub(r'<[^>]+>', '', highlighted_text_segment)
    if not clean_highlight.strip(): # Si le highlight est vide après nettoyage (ex: juste un espace)
        return -1 # Impossible de localiser

    current_char_count = 0
    text_to_search_in = clean_full_text_from_srt # Le texte complet tel qu'il apparaît dans le bloc SRT

    # Trouver le début du segment en surbrillance dans le texte complet du bloc SRT
    # (après avoir nettoyé les balises pour le positionnement)
    start_offset_in_clean_srt_text = text_to_search_in.find(clean_highlight)

    if start_offset_in_clean_srt_text == -1:
        # Essayer une recherche plus souple si la casse ou les espaces diffèrent
        # Cette partie peut nécessiter des techniques de "fuzzy search" ou d'alignement de séquences
        # pour être vraiment robuste. Pour l'instant, on reste simple.
        print(f"Avertissement: Segment en surbrillance '{clean_highlight}' non trouvé tel quel dans le texte du bloc SRT nettoyé.")
        # Tentative de recherche en ignorant la casse et les espaces multiples
        normalized_text_to_search = ' '.join(text_to_search_in.lower().split())
        normalized_clean_highlight = ' '.join(clean_highlight.lower().split())
        start_offset_in_clean_srt_text = normalized_text_to_search.find(normalized_clean_highlight)
        if start_offset_in_clean_srt_text == -1:
            print(f"Échec de la localisation de '{clean_highlight}'.")
            return -1 # Non trouvé

    # Maintenant, mapper cet offset aux lignes originales
    cumulative_len = 0
    for i, line in enumerate(original_lines):
        clean_original_line = line.strip() # Utiliser la ligne telle quelle pour la longueur
        line_len = len(clean_original_line)
        # Si le début du segment est dans la portée de cette ligne originale
        if cumulative_len <= start_offset_in_clean_srt_text < cumulative_len + line_len + 1: # +1 pour l'espace/newline
            return i
        cumulative_len += line_len + 1 # +1 pour simuler un séparateur de ligne (espace ou newline)

    return -1 # Non trouvé

def postprocess_srt(input_srt_path, original_lyrics_path, output_srt_path, display_mode):
    """
    Génère le fichier SRT post-traité selon le display_mode.
    """
    srt_blocks = parse_srt_file(input_srt_path)
    original_lines = load_original_lyrics(original_lyrics_path)

    output_blocks = []
    block_index = 1

    if not srt_blocks:
        print("Aucun bloc trouvé dans le fichier SRT d'entrée.")
        return

    if display_mode == "word": # Anciennement 'full_text_highlight'
        # Le SRT d'entrée est déjà dans un format où chaque bloc est un "mot" ou segment mis en évidence
        # mais le texte du bloc est l'intégralité des paroles.
        # On veut que le texte du bloc de sortie soit *uniquement* le mot/segment en surbrillance.
        print("Mode 'word': chaque bloc SRT contiendra uniquement le segment en surbrillance.")
        for block in srt_blocks:
            match_highlight = HIGHLIGHT_PATTERN.match(block["text_with_highlight"])
            if match_highlight:
                _, highlighted_text, _ = match_highlight.groups()
                if highlighted_text.strip(): # Ne pas créer de blocs pour des surbrillances vides
                    output_blocks.append(f"{block_index}\n"
                                         f"{block['start_time']} --> {block['end_time']}\n"
                                         f"{highlighted_text.strip()}\n")
                    block_index += 1
            else: # Pas de surbrillance trouvée, on garde le texte tel quel (ou on le logue)
                print(f"Avertissement: Aucune surbrillance trouvée dans le bloc {block['index']} pour le mode 'word'. Texte original: {block['text_with_highlight']}")
                # On pourrait choisir de copier le bloc original ou de l'omettre. Pour l'instant, on l'omet.

    elif display_mode == "line" or display_mode == "line_plus_next":
        print(f"Mode '{display_mode}': reconstruction des lignes.")
        for block in srt_blocks:
            match_highlight = HIGHLIGHT_PATTERN.match(block["text_with_highlight"])
            if not match_highlight:
                print(f"Avertissement: Aucune surbrillance trouvée dans le bloc {block['index']}.")
                continue

            text_before, highlighted_segment, text_after = match_highlight.groups()

            # Pour reconstruire la ligne originale avec la surbrillance, on a besoin de savoir quelle ligne c'est.
            # La fonction find_line_index_for_highlighted_text est une tentative, mais elle est complexe.
            # Une approche plus simple ici, étant donné le format d'entrée, est de supposer que le texte
            # du bloc SRT *est* déjà la structure complète.
            # La difficulté est de savoir quelle ligne originale est la "courante".
            # On va devoir itérer sur les lignes originales et essayer de faire un "best effort"
            # pour trouver la ligne qui contient le `highlighted_segment`.

            # Cette logique doit être affinée. Pour l'instant, une version simplifiée :
            # On va juste utiliser le texte complet du bloc SRT et s'assurer que la surbrillance est là.
            # Le découpage en "ligne originale" sera pour plus tard si cette approche est insuffisante.

            line_idx = find_line_index_for_highlighted_text(original_lines, highlighted_segment, text_before, text_after)

            if line_idx != -1:
                current_line_original_text = original_lines[line_idx]

                # Comment réinsérer la surbrillance dans la ligne originale ?
                # On prend le `highlighted_segment` (qui a déjà les <font>)
                # et on le met dans `current_line_original_text`.
                # Il faut remplacer la version non-highlightée du segment dans la ligne originale.
                clean_highlighted_segment = re.sub(r'<[^>]+>', '', highlighted_segment)

                if not clean_highlighted_segment.strip() and highlighted_segment.strip(): # ex: <font> </font>
                     # Si le highlight est juste un espace formaté, on le traite comme un espace.
                    final_text_for_block = current_line_original_text # Pas de highlight spécifique à insérer
                elif clean_highlighted_segment.strip():
                    # Remplacer la première occurrence du segment propre par le segment avec balises
                    # Ceci est une simplification, peut échouer si le segment apparaît plusieurs fois.
                    # Une approche plus robuste utiliserait les offsets.
                    # Pour l'instant, on suppose que `highlighted_segment` est le texte à afficher.
                    # Et que `current_line_original_text` est la ligne où il doit apparaître.

                    # Nouvelle stratégie : on reconstruit la ligne originale avec le mot surligné.
                    # On a text_before, highlighted_segment, text_after qui forment l'intégralité des paroles.
                    # On doit trouver où se situe la ligne originale `original_lines[line_idx]`
                    # dans cet ensemble.

                    # Pour le mode 'line': afficher original_lines[line_idx] avec son mot surligné.
                    # Le `highlighted_segment` est déjà le mot avec les balises font.
                    # On doit trouver ce mot (sans balises) dans `original_lines[line_idx]` et le remplacer.

                    temp_line = original_lines[line_idx]
                    # Il faut être prudent avec les remplacements pour ne pas corrompre les balises.
                    # On va essayer de remplacer la version "propre" du highlight par la version "avec balises".
                    # Cela suppose que `clean_highlighted_segment` est un sous-ensemble de `temp_line`.

                    # Ceci est complexe. Pour une V1, on va simplifier :
                    # Le texte affiché est la ligne originale, et on espère que le lecteur
                    # saura gérer la surbrillance si le timing est bon pour le mot.
                    # Mais le SRT doit contenir le texte à afficher.
                    # On va donc essayer de reconstruire la ligne originale, et y insérer le segment surligné.

                    # Si on a `text_before_highlight`, `highlighted_segment`, `text_after_highlight`
                    # qui constituent l'ENSEMBLE des paroles.
                    # Et `original_lines` sont les lignes de base.
                    # On doit trouver à quelle ligne appartient `highlighted_segment`.

                    # Simplification pour la V1 du postprocesseur:
                    # On va prendre le texte complet du bloc SRT d'entrée (qui a déjà la surbrillance)
                    # et le présenter. Ce n'est pas encore le mode 'b' ou 'c' désiré.
                    # C'est en fait une copie du mode 'a' pour l'instant.
                    # La logique de découpage en lignes originales sera une amélioration future.

                    # Pour vraiment faire mode 'b' et 'c', il faut :
                    # 1. Savoir quel est le "mot/syllabe" courant (le `highlighted_segment`).
                    # 2. Trouver ce mot/syllabe dans les `original_lines` pour identifier la ligne courante.
                    # 3. Reconstruire cette ligne originale en y insérant le `highlighted_segment` (avec ses balises <font>).
                    # 4. Pour mode 'c', ajouter la ligne suivante des `original_lines`.

                    # Pour l'instant, cette fonction est un placeholder pour la logique complexe.
                    # On va commencer par le mode 'word' qui est plus simple.
                    # Et pour 'line'/'line_plus_next', on va copier le texte du bloc d'entrée
                    # en attendant une logique plus fine.

                    output_text = block["text_with_highlight"] # Placeholder

                    if display_mode == "line":
                        # TODO: Isoler la ligne courante à partir de `original_lines` et `highlighted_segment`
                        # Pour l'instant, on retourne le texte complet du bloc (comme mode 'a')
                        # en attendant la logique de mapping de ligne.
                        # output_text = "LOGIQUE LIGNE COURANTE A IMPLEMENTER"
                        pass # On garde output_text = block["text_with_highlight"]

                    elif display_mode == "line_plus_next":
                        # TODO: Isoler ligne courante + suivante
                        # output_text = "LOGIQUE LIGNE COURANTE + SUIVANTE A IMPLEMENTER"
                        if line_idx + 1 < len(original_lines):
                            # output_text += "\n" + original_lines[line_idx+1] # Brut, sans gestion de surbrillance
                            pass


                    output_blocks.append(f"{block_index}\n"
                                         f"{block['start_time']} --> {block['end_time']}\n"
                                         f"{output_text.strip()}\n")
                    block_index += 1
            else:
                # Fallback si on n'a pas pu localiser la ligne (devrait peu arriver si SRT est bien formé)
                 output_blocks.append(f"{block_index}\n"
                                     f"{block['start_time']} --> {block['end_time']}\n"
                                     f"{block['text_with_highlight'].strip()}\n")
                 block_index +=1


    with open(output_srt_path, 'w', encoding='utf-8') as f:
        for i, block_str in enumerate(output_blocks):
            f.write(block_str)
            if i < len(output_blocks) - 1: # Ajouter un newline entre les blocs, sauf pour le dernier
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
            "  'line': Chaque entrée SRT affichera la ligne de paroles originale complète où se trouve le mot/segment en surbrillance, avec ce dernier coloré.\n"
            "          (Implémentation actuelle pour 'line' et 'line_plus_next' est simplifiée et copie le bloc d'entrée en attendant une logique de mapping plus fine).\n"
            "  'line_plus_next': Comme 'line', mais affiche aussi la ligne de paroles originale suivante."
        )
    )
    # TODO: Ajouter une option pour la couleur de surbrillance ? Pour l'instant, on suppose qu'elle est dans l'entrée.

    args = parser.parse_args()

    try:
        postprocess_srt(args.input_srt_file, args.original_lyrics_file, args.output_srt_file, args.display_mode)
    except FileNotFoundError as e:
        print(f"Erreur : {e}")
    except Exception as e:
        print(f"Une erreur inattendue est survenue : {e}")

if __name__ == "__main__":
    main()
