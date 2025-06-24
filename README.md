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
        *   Génère des timestamps au niveau du mot, produisant un fichier LRC Enhanced.
        *   **Dépendances importantes :** `stable-ts`, `torch`, `torchaudio`, `openai-whisper`. PyTorch et les modèles Whisper peuvent être volumineux. L'exécution se fait sur CPU par défaut dans le script, ce qui peut être lent pour les gros modèles ou les longues chansons.
        *   Les modèles Whisper sont téléchargés automatiquement par la bibliothèque lors de la première utilisation d'un modèle spécifique.
        *   Commande : `python script/sync_lyrics.py audio.mp3 paroles.txt --mode auto_stablets --st_model base --st_lang ja`
            *   `--st_model` : Choix du modèle Whisper (ex: `tiny`, `base`, `small`, `medium`). Les plus petits sont plus rapides mais moins précis.
            *   `--st_lang` : Code langue pour Whisper (ex: `ja` pour japonais, `en` pour anglais).

## Structure des documents d'analyse (dans `docs/`)
*   `01_context_fonctionnel_et_technique.md`: Contexte du projet.
*   `02_objectifs_et_roadmap_iterative.md`: Objectifs et roadmap.
*   `03_detection_musique_en_cours.md`: Exploration de la détection de la musique.
*   `04_recherche_lyrics_romaji.md`: Exploration de la recherche de paroles.
*   `05_affichage_lyrics.md`: Exploration des options d'affichage des LRC.
*   `06_formats_paroles_synchronisees.md`: Analyse des formats de fichiers LRC, SRT, ASS.
*   `07_synchronisation_automatique.md`: Exploration des outils d'alignement automatique.