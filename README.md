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
        *   `word` (défaut) : Chaque entrée SRT dans le fichier de sortie contient uniquement le mot/segment qui était en surbrillance dans le fichier d'entrée.
        *   `line` : Chaque entrée SRT affiche la ligne de paroles originale complète où se trouve le mot/segment en surbrillance.
        *   `line_plus_next` : Comme `line`, mais affiche aussi la ligne de paroles originale suivante.
    *   **Styles de surbrillance (`--highlight_style`) pour les modes `line` et `line_plus_next` (et partiellement `word`) :**
        *   `preserve` (défaut) : Conserve la surbrillance `<font ...>` du segment d'origine tel qu'il est inséré dans la ligne courante. En mode `line_plus_next`, la ligne suivante est affichée en gris (`<font color="#aaaaaa">...</font>`).
        *   `line_all` : Met en surbrillance l'intégralité de la ligne courante en couleur principale (ex: `#00ff00`). En mode `line_plus_next`, la ligne suivante est également mise en surbrillance mais en gris (`<font color="#aaaaaa">...</font>`). Pour le mode `word`, surligne le mot isolé avec la couleur principale.
        *   `none` : Aucune surbrillance. Affiche le texte brut des lignes (ou du mot pour le mode `word`).
    *   *Note : La robustesse du positionnement de la surbrillance dans les modes `line` et `line_plus_next` dépend de la cohérence entre le texte du SRT d'entrée et les paroles originales.*

## Structure des documents d'analyse (dans `docs/`)
*   `01_context_fonctionnel_et_technique.md`: Contexte du projet.
*   `02_objectifs_et_roadmap_iterative.md`: Objectifs et roadmap.
*   `03_detection_musique_en_cours.md`: Exploration de la détection de la musique.
*   `04_recherche_lyrics_romaji.md`: Exploration de la recherche de paroles.
*   `05_affichage_lyrics.md`: Exploration des options d'affichage des LRC.
*   `06_formats_paroles_synchronisees.md`: Analyse des formats de fichiers LRC, SRT, ASS.
*   `07_synchronisation_automatique.md`: Exploration des outils d'alignement automatique.