# 01 - Contexte fonctionnel et technique

## Contexte fonctionnel

### Contexte fonctionnel
- L'utilisateur écoute principalement des chansons en japonais (et marginalement en anglais, français, espagnol).
- Les chansons sont écoutées via :
  - La plateforme **Deezer** (via navigateur ou outil de téléchargement `deemix`).
  - Le lecteur local **`mplayer`**.
- Objectif : accéder automatiquement aux **lyrics en romaji** (translittération latine du japonais) des chansons en cours de lecture.

### Contexte technique
- OS : **Ubuntu 24.04**.
- Fichiers `.mp3` extraits depuis Deezer via **`deemix`**.
- Les fichiers `.mp3` contiennent les **tags ID3** (titre, artiste).
- Script Python principal (`lyrics_fetcher_cli.py`) utilisé en CLI, prenant en paramètre un fichier mp3 ou détectant automatiquement les tags.
- Affichage actuel : dump brut des lyrics dans le terminal.

## Problèmes identifiés

### Sur Deezer
- Les paroles ne sont pas toujours disponibles.
- Quand elles le sont, elles sont généralement en kanji/hiragana/katakana.
- Les informations de chanson (titre, artiste, etc.) sont disponibles dans l’interface et/ou via API.

### Sur mplayer
- Pas de système natif d’affichage des paroles.
- Les fichiers `.mp3` n’intègrent pas de paroles.
- Les métadonnées (tags ID3) contiennent les informations nécessaires (titre, artiste...)


