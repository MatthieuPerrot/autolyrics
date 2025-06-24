#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour convertir un fichier texte de Romaji en Kana (Hiragana/Katakana).
Utilise la bibliothèque cutlet.
"""

import argparse
import os
import cutlet # Import cutlet

# Initialiser cutlet. katsu est l'objet principal pour la conversion.
# unidic-lite devrait être trouvé automatiquement s'il est installé.
try:
    katsu = cutlet.Cutlet()
except Exception as e:
    print(f"Erreur lors de l'initialisation de Cutlet : {e}")
    print("Assurez-vous que 'unidic-lite' est installé (`pip install unidic-lite`).")
    katsu = None

def convert_line_romaji_to_kana(line, mode="hira"):
    """
    Convertit une seule ligne de romaji en kana.

    Args:
        line (str): La ligne de texte en romaji.
        mode (str): 'hira' pour hiragana, 'kata' pour katakana.

    Returns:
        str: La ligne convertie en kana.
    """
    if not katsu:
        raise RuntimeError("Cutlet n'a pas été initialisé correctement.")
    line = line.strip().lower()
    if not line:
        return ""

    # Cutlet peut nécessiter une tokenization si la ligne est complexe,
    # mais pour une conversion simple, on peut essayer de passer la ligne entière.
    # Cutlet gère différents systèmes de romaji.
    # La sortie par défaut est en katakana pour les mots étrangers, hiragana pour le reste.

    kana_system_target = 'hira' # Par défaut Hiragana
    if mode.lower() == 'k':
        kana_system_target = 'kata'
    elif mode.lower() == 'h':
        kana_system_target = 'hira'
    # On pourrait ajouter 'auto' si on veut un mix intelligent, mais pour les paroles,
    # forcer en hiragana est souvent plus cohérent, sauf pour les mots d'emprunt.
    try:
        # Tenter de convertir la ligne. Cutlet peut lever des erreurs si le romaji est ambigu
        # ou s'il contient des parties non convertibles qu'il ne sait pas ignorer par défaut.
        # Pour des paroles, il est possible qu'il y ait des mots anglais ou des onomatopées.
        # On va essayer de segmenter par espace et convertir chaque "mot"
        # pour mieux gérer les parties non-japonaises.
        words = line.split(' ')
        converted_words = []
        for word in words:
            if not word:
                continue
            # Vérifier si le mot est purement ASCII et pourrait être un mot étranger/onomatopée
            # que cutlet ne devrait pas essayer de convertir ou convertirait mal.
            # C'est une heuristique simple.
            try:
                if kana_system_target == 'hira':
                    converted_segment = cutlet.jaconv.alphabet2kana(word)
                # Si la conversion ne change rien pour un mot purement ascii,
                # ou produit quelque chose d'étrange, on pourrait préférer l'original.
                # Pour l'instant, on fait confiance à cutlet.
                elif kana_system_target == 'kata':
                    converted_segment = cutlet.jaconv.alphabet2kata(word)
                converted_words.append(converted_segment)
            except Exception as e: # Si cutlet échoue sur un mot spécifique
                print(f"Avertissement : Impossible de convertir le mot '{word}' : {e}. Il sera gardé en l'état.")
                converted_words.append(word) # Garder le mot original
        return ' '.join(converted_words)

    except Exception as e:
        print(f"Avertissement : Impossible de convertir la ligne '{line}' : {e}. Elle sera gardée en l'état.")
        # Pour l'instant, si la ligne entière échoue, on la garde en l'état.
        # Une meilleure gestion serait de convertir mot à mot et de garder les mots problématiques en romaji.
        # La logique ci-dessus tente déjà cela.
        print(f"Avertissement sur la ligne : '{line}'. Certains mots pourraient ne pas être convertis.")
        return line # Retourner la ligne originale en cas d'échec global non géré par le split


def convert_file_romaji_to_kana(input_filepath, output_filepath, mode="H"):
    """
    Lit un fichier texte en romaji, le convertit en kana, et écrit le résultat
    dans un fichier de sortie.
    """
    if not katsu:
        print("Erreur: Cutlet n'est pas initialisé. Impossible de convertir.")
        return

    if not os.path.exists(input_filepath):
        print(f"Erreur : Fichier d'entrée introuvable : {input_filepath}")
        return

    print(f"Début de la conversion de {input_filepath} vers {output_filepath} (mode: {mode})")
    line_count = 0
    converted_count = 0
    try:
        with open(input_filepath, 'r', encoding='utf-8') as infile, \
             open(output_filepath, 'w', encoding='utf-8') as outfile:
            for line in infile:
                line_count += 1
                original_line = line.strip()
                if not original_line:
                    outfile.write("\n")
                    continue
                converted_line = convert_line_romaji_to_kana(original_line, mode)
                outfile.write(converted_line + "\n")
                if original_line != converted_line: # Simple vérification si quelque chose a changé
                    converted_count +=1
        print(f"Conversion terminée. {converted_count}/{line_count} lignes ont été modifiées (approximativement).")
        print(f"Fichier de sortie : {output_filepath}")

    except Exception as e:
        print(f"Une erreur est survenue lors de la conversion du fichier : {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Convertit un fichier texte de Romaji en Kana (Hiragana ou Katakana) en utilisant Cutlet.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_file", help="Chemin vers le fichier .txt d'entrée (Romaji).")
    parser.add_argument("output_file", help="Chemin vers le fichier .txt de sortie (Kana).")
    parser.add_argument(
        "--mode",
        choices=["H", "K"],
        default="H",
        help="Mode de conversion en Kana:\n"
             "H: Hiragana (défaut, les mots d'emprunt peuvent rester en Katakana si 'auto' était utilisé)\n"
             "K: Katakana"
    )

    args = parser.parse_args()

    if not katsu:
        print("Cutlet n'a pas pu être initialisé. Vérifiez les messages d'erreur précédents.")
        return

    convert_file_romaji_to_kana(args.input_file, args.output_file, args.mode.lower())

if __name__ == "__main__":
    main()
