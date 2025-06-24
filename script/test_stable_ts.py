#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de test pour la bibliothèque stable-ts (basée sur Whisper)
pour l'alignement audio-texte (paroles).
"""

import argparse
import os
import stable_whisper
import json
import time

def test_stable_ts_alignment(audio_path, text_path, model_name="base", output_json_path=None, language='ja'):
    """
    Teste l'alignement audio-texte avec stable-ts.

    Args:
        audio_path (str): Chemin vers le fichier audio (MP3, WAV, etc.).
        text_path (str): Chemin vers le fichier texte des paroles (Romaji ou Kana).
        model_name (str): Nom du modèle Whisper à utiliser (ex: "tiny", "base", "small", "medium", "large").
        output_json_path (str, optional): Chemin pour sauvegarder le résultat JSON.
                                           Si None, le résultat est printé.
        language (str): Code langue pour Whisper (ex: 'ja' pour japonais, 'en' pour anglais).
    """
    if not os.path.exists(audio_path):
        print(f"Erreur : Fichier audio introuvable : {audio_path}")
        return
    if not os.path.exists(text_path):
        print(f"Erreur : Fichier texte introuvable : {text_path}")
        return

    print(f"Chargement du modèle Whisper '{model_name}' via stable-ts. Cela peut prendre du temps...")
    try:
        # stable_whisper.load_model peut aussi prendre des device="cpu"
        # mais stable-ts le gère souvent en interne s'il ne trouve pas de GPU.
        model = stable_whisper.load_model(model_name, device="cpu")
        print("Modèle chargé.")
    except Exception as e:
        print(f"Erreur lors du chargement du modèle Whisper '{model_name}': {e}")
        print("Assurez-vous que PyTorch est installé et que le nom du modèle est correct.")
        print("Les modèles sont téléchargés automatiquement lors de la première utilisation.")
        return

    print(f"Lecture du fichier texte : {text_path}")
    with open(text_path, 'r', encoding='utf-8') as f:
        text_content = f.read()

    if not text_content.strip():
        print("Erreur : Le fichier texte est vide.")
        return

    print(f"Début de l'alignement de '{audio_path}' avec le texte fourni...")
    start_time = time.time()

    try:
        # Utilisation de la fonction 'align' de stable-ts qui est conçue pour aligner
        # un audio sur un texte existant.
        # La documentation de stable-ts peut offrir plus d'options de réglage fin.
        # Par défaut, il devrait essayer de faire un alignement au niveau du mot.
        # 'regroup=False' est important pour obtenir des segments plus fins (mots).
        # 'suppress_silence=True' et 'suppress_word_ts=False' sont les valeurs par défaut
        # qui devraient fonctionner pour obtenir les timestamps des mots.
        result = model.align(audio_path, text_content, language=language, regroup=False)

        # Alternativement, si `align` n'est pas la bonne fonction ou si on veut plus de contrôle
        # avec la transcription puis l'ajustement des timestamps :
        # result = model.transcribe(audio_path, language=language)
        # result_aligned = stable_whisper.stabilize_timestamps(result, text_content)
        # Mais `align` est plus direct pour notre cas d'usage.

    except Exception as e:
        print(f"Erreur lors de l'alignement avec stable-ts : {e}")
        return

    end_time = time.time()
    print(f"Alignement terminé en {end_time - start_time:.2f} secondes.")

    # La structure de 'result' dépend de la version et des options de stable-ts.
    # Typiquement, c'est un objet ou un dictionnaire avec une clé 'segments'
    # et chaque segment contient des 'words' avec 'word', 'start', 'end'.

    # Tentative de sérialisation en JSON pour inspection
    # L'objet `result` de stable-ts est un objet `WhisperResult` qui a une méthode `to_dict()`
    # et aussi `to_srt_vtt()` ou `to_ass()`

    try:
        result_dict = result.to_dict()

        if output_json_path:
            print(f"Sauvegarde du résultat JSON dans : {output_json_path}")
            with open(output_json_path, 'w', encoding='utf-8') as f_json:
                json.dump(result_dict, f_json, indent=2, ensure_ascii=False)
        else:
            print("\nRésultat de l'alignement (JSON) :")
            print(json.dumps(result_dict, indent=2, ensure_ascii=False))

        # Affichage simplifié des mots et de leurs timestamps
        print("\nSegments de mots alignés :")
        for segment in result.segments:
            for word_info in segment.words:
                start = word_info.start
                end = word_info.end
                word_text = word_info.word
                print(f"  [{start:.3f}s - {end:.3f}s] \"{word_text}\"")

        # On peut aussi générer un SRT directement pour un test visuel
        srt_output_path = os.path.splitext(audio_path)[0] + f"_stable_ts_{model_name}.srt"
        result.to_srt_vtt(srt_output_path, word_level=True)
        print(f"\nFichier SRT (niveau mot) généré pour test visuel : {srt_output_path}")


    except Exception as e:
        print(f"Erreur lors du traitement ou de la sauvegarde du résultat : {e}")
        print("Résultat brut de stable-ts :")
        print(result)


def main():
    parser = argparse.ArgumentParser(
        description="Teste l'alignement audio-texte avec stable-ts (Whisper).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("audio_path", help="Chemin vers le fichier audio (MP3, WAV, etc.).")
    parser.add_argument("text_path", help="Chemin vers le fichier texte des paroles (Romaji ou Kana).")
    parser.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large", "large-v1", "large-v2", "large-v3"],
        help="Nom du modèle Whisper à utiliser."
    )
    parser.add_argument(
        "--lang",
        default="ja",
        help="Code langue pour Whisper (ex: 'ja' pour japonais, 'en' pour anglais)."
    )
    parser.add_argument(
        "--output_json",
        help="Chemin optionnel pour sauvegarder le résultat complet de l'alignement en JSON."
    )

    args = parser.parse_args()

    # Vérification si les dépendances majeures sont là (au cas où pip install aurait échoué en silence)
    try:
        import torch
        import torchaudio
        print(f"PyTorch version: {torch.__version__}, Torchaudio version: {torchaudio.__version__}")
        # Vérifier si CUDA est disponible (indicatif, stable-ts devrait utiliser CPU si non)
        if torch.cuda.is_available():
            print(f"CUDA est disponible. GPU: {torch.cuda.get_device_name(0)}")
        else:
            print("CUDA non disponible. PyTorch utilisera le CPU.")
    except ImportError as ie:
        print(f"Erreur d'importation : {ie}. Assurez-vous que PyTorch et Torchaudio sont installés.")
        print("pip install torch torchaudio stable-ts openai-whisper")
        return

    test_stable_ts_alignment(args.audio_path, args.text_path, args.model, args.output_json, args.lang)

if __name__ == "__main__":
    main()
