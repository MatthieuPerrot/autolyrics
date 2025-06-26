#!/bin/bash

# Script pour tester l'affichage overlay avec mpv sous Wayland

# MODIFIEZ CETTE LIGNE POUR TESTER DIFFERENTS VO:
# Options possibles: "gpu", "gpu-next", "wlshm"
VIDEO_OUTPUT="gpu"
# VIDEO_OUTPUT="gpu-next"
# VIDEO_OUTPUT="wlshm"

AUDIO_FILE="test_audio.mp3"
SRT_FILE="test_lyrics.srt"
WINDOW_TITLE="MPV_LYRICS_OVERLAY"

# Vérifier si les fichiers de test existent
if [ ! -f "$AUDIO_FILE" ]; then
    echo "Fichier audio '$AUDIO_FILE' non trouvé !"
    exit 1
fi

if [ ! -f "$SRT_FILE" ]; then
    echo "Fichier SRT '$SRT_FILE' non trouvé !"
    exit 1
fi

echo "Lancement de mpv avec --vo=$VIDEO_OUTPUT ..."

# Lancer mpv avec les options pour l'overlay
mpv \
    --title="$WINDOW_TITLE" \
    --no-border \
    --ontop \
    --geometry=80%x15%+10%-5% \
    --input-cursor-passthrough=yes \
    --no-video \
    --force-window=yes \
    --audio-display=no \
    --vo="$VIDEO_OUTPUT" \
    --gpu-context=wayland \
    --wayland-app-id="org.mpv_lyrics_overlay.Mpv" \
    --background="#00000000" \
    --sub-file="$SRT_FILE" \
    --sub-font-size=38 \
    --sub-color="#FFFFFF" \
    --sub-border-color="#000000" \
    --sub-border-size=1.2 \
    --sub-align-y=bottom \
    --sub-margin-y=20 \
    --loop=inf \
    "$AUDIO_FILE"

echo "mpv terminé."
