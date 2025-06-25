# autolyrics

Ce projet contient des scripts pour récupérer et synchroniser des paroles de chansons.

## Fonctionnalités

1.  **Récupération de paroles (`script/lyrics_fetcher_cli.py`)**
    *   Extrait les métadonnées (titre, artiste) d'un fichier MP3.
    *   Recherche automatiquement les paroles en romaji sur internet.
    *   Sauvegarde les paroles brutes dans un fichier `.txt`.
    *   Peut lancer le script de synchronisation.

2.  **Synchronisation de paroles (`script/sync_lyrics.py`)**
    *   Permet de créer des fichiers de paroles synchronisées (`.lrc`) à partir d'un fichier MP3 et d'un fichier `.txt` de paroles.
    *   **Mode manuel (ligne par ligne) :**
        *   Joue le MP3 et permet à l'utilisateur d'appuyer sur une touche pour marquer le début de chaque ligne de parole.
        *   Utilise `pygame` pour la lecture audio.
        *   Commande : `python script/sync_lyrics.py audio.mp3 paroles.txt --mode line`
    *   **Mode automatique avec `stable-ts` (basé sur Whisper) :**
        *   Utilise le modèle de reconnaissance vocale Whisper via `stable-ts` pour aligner automatiquement les paroles (fournies dans le fichier `.txt`) avec l'audio.
        *   Utilise le modèle de reconnaissance vocale Whisper via `stable-ts` pour aligner automatiquement les paroles (fournies dans le fichier `.txt`) avec l'audio.
        *   Génère un fichier `.srt` détaillé où chaque entrée correspond à un segment (mot/syllabe) mis en évidence, avec le texte complet des paroles répété dans chaque entrée et la partie active colorée (formatage dépendant de `stable-ts`).
        *   **Dépendances importantes :** `stable-ts`, `torch`, `torchaudio`, `openai-whisper`. PyTorch et les modèles Whisper peuvent être volumineux. L'exécution se fait sur CPU par défaut dans le script.
        *   Les modèles Whisper sont téléchargés automatiquement lors de la première utilisation.
        *   Commande : `python script/sync_lyrics.py audio.mp3 paroles.txt --mode auto_stablets --st_model base --st_lang ja`
            *   `--st_model` : Choix du modèle Whisper (ex: `tiny`, `base`, `small`).
            *   `--st_lang` : Code langue pour Whisper (ex: `ja`, `en`).
            *   La sortie sera un fichier `.srt` (ex: `audio.srt`).

3.  **Post-traitement de fichiers SRT (`script/postprocess_srt.py`)**
    *   Permet de transformer le fichier SRT détaillé généré par `sync_lyrics.py --mode auto_stablets` en différents formats d'affichage.
    *   Prend en entrée le `.srt` détaillé et le fichier `.txt` des paroles originales (pour la structure des lignes).
    *   Commande : `python script/postprocess_srt.py input_detailed.srt original_lyrics.txt output_processed.srt --display_mode <mode>`
    *   **Modes d'affichage (`--display_mode`) :**
        *   `word` (défaut) : Chaque entrée SRT dans le fichier de sortie contient uniquement le mot/segment qui était en surbrillance dans le fichier d'entrée. Ce mode est fonctionnel.
        *   `line` : **(En développement)** Vise à afficher la ligne de paroles originale complète où se trouve le mot/segment en surbrillance, avec ce dernier conservant sa surbrillance. L'implémentation actuelle est préliminaire.
        *   `line_plus_next` : **(En développement)** Vise à faire comme `line`, mais affiche aussi la ligne de paroles originale suivante. L'implémentation actuelle est préliminaire.

## Structure des documents d'analyse (dans `docs/`)
*   `01_context_fonctionnel_et_technique.md`: Contexte du projet.
*   `02_objectifs_et_roadmap_iterative.md`: Objectifs et roadmap.
*   `03_detection_musique_en_cours.md`: Exploration de la détection de la musique.
*   `04_recherche_lyrics_romaji.md`: Exploration de la recherche de paroles.
*   `05_affichage_lyrics.md`: Exploration des options d'affichage des LRC.
*   `06_formats_paroles_synchronisees.md`: Analyse des formats de fichiers LRC, SRT, ASS.
*   `07_synchronisation_automatique.md`: Exploration des outils d'alignement automatique.