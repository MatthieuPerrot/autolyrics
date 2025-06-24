#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour convertir un fichier texte de Romaji en Kana (Hiragana/Katakana).
Utilise la bibliothèque pykakasi.
"""

import argparse
import os
from pykakasi import kakasi

def convert_file_romaji_to_kana(input_filepath, output_filepath, to_kana_mode="H"):
    """
    Lit un fichier texte en romaji, le convertit en kana, et écrit le résultat
    dans un fichier de sortie.

    Args:
        input_filepath (str): Chemin du fichier d'entrée (romaji).
        output_filepath (str): Chemin du fichier de sortie (kana).
        to_kana_mode (str): Mode de conversion vers Kana.
                             'H' pour Hiragana (défaut),
                             'K' pour Katakana,
                             'J' pour Kanji (si applicable, pykakasi le fait via J-H-K).
                             En pratique pour les paroles, Hiragana est souvent le plus utile.
    """
    if not os.path.exists(input_filepath):
        print(f"Erreur : Fichier d'entrée introuvable : {input_filepath}")
        return

    kks = kakasi()
    # Configuration pour convertir en Hiragana, Katakana, ou Kanji.
    # Pour les paroles, la cible principale est Hiragana (H) ou Katakana (K).
    # 'J' (Kanji) + 'H' (Hiragana) + 'K' (Katakana) sont les options de sortie.
    # 'a' (Ascii) pour la sortie de la phonétique (Hepburn romaji), 'r' (Romaji)
    # 's' (space) pour ajouter des espaces entre les mots convertis.
    # 'E' (pas de conversion)
    
    # Mode simple : convertir tout ce qui est possible dans le mode cible (H, K, ou J)
    conversion_config = {
        "J": True, # Convertir en Kanji (si possible, sinon reste en kana/romaji)
        "H": True, # Convertir en Hiragana
        "K": True, # Convertir en Katakana
        "a": False, # Ne pas sortir en Romaji (on part du Romaji)
        "r": False, # Idem
        "s": False, # Ne pas ajouter d'espaces supplémentaires par défaut
        "E": False,
        "orig": False, # Ne pas inclure le texte original
        "kana": True, # Sortie en Kana
        "hepburn": False, # Pas de sortie Hepburn
        "kunrei": False, # Pas de sortie Kunrei
        "passport": False # Pas de sortie Passport
    }
    
    # Ajuster pour le mode spécifique désiré (H, K, J)
    # pykakasi convertit en plusieurs étapes et le filtre final se fait sur `kana`
    # Si on veut que H, K, ou J soit le mode principal, on le spécifie.
    # La doc de pykakasi indique que pour `convert()`, on itère sur les résultats.
    # Chaque résultat a des clés 'orig', 'hira', 'kana', 'kunrei', 'hepburn'.
    # 'kana' contient le résultat après conversion J-H-K.

    try:
        with open(input_filepath, 'r', encoding='utf-8') as infile, \
             open(output_filepath, 'w', encoding='utf-8') as outfile:
            
            for line_num, line in enumerate(infile):
                line = line.strip()
                if not line:
                    outfile.write("\n")
                    continue

                result = kks.convert(line)
                converted_line_parts = []
                for item in result:
                    # Selon le mode, on choisit la sortie.
                    # 'hira' pour Hiragana, 'kata' pour Katakana.
                    # 'kana' est souvent un bon choix général car il contient le résultat
                    # de la conversion (peut être un mélange si des mots sont mieux en katakana).
                    # Pour forcer un mode spécifique, il faut être plus précis.
                    # Pour l'instant, utilisons 'hira' comme cible principale si 'H', 'kata' si 'K'.
                    # 'kana' est un bon fallback.
                    if to_kana_mode.upper() == "H":
                        converted_line_parts.append(item['hira'])
                    elif to_kana_mode.upper() == "K":
                        converted_line_parts.append(item['kata'])
                    else: # Fallback ou si on veut le mix par défaut de pykakasi
                        converted_line_parts.append(item['kana'])
                
                outfile.write("".join(converted_line_parts) + "\n")
        
        print(f"Conversion terminée. Fichier de sortie : {output_filepath}")

    except Exception as e:
        print(f"Une erreur est survenue lors de la conversion : {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Convertit un fichier texte de Romaji en Kana (principalement Hiragana).",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_file", help="Chemin vers le fichier .txt d'entrée (Romaji).")
    parser.add_argument("output_file", help="Chemin vers le fichier .txt de sortie (Kana).")
    parser.add_argument(
        "--mode",
        choices=["H", "K", "J"], # (Kanji) est plus complexe et moins direct pour la parole
        default="J",
        help="Mode de conversion en Kana:\n"
             "H: Hiragana (défaut)\n"
             "K: Katakana"
    )

    args = parser.parse_args()

    convert_file_romaji_to_kana(args.input_file, args.output_file, args.mode)

if __name__ == "__main__":
    main()
