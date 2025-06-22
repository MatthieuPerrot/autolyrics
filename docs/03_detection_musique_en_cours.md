
## Méthode utilisée pour `mplayer`
```bash
./lyrics_fetcher_cli.py "$(lsof  -c mplayer -F 2>/dev/null | cut -c 2- | grep '\.mp3')"
```
- Avantage : pas besoin de plugin ni d’intégration profonde.
- Limite : uniquement utilisable si mplayer est lancé depuis le même environnement.

## Alternatives envisagées (non implémentées à ce jour)
- Hook direct dans `mplayer` (avec FIFO ou `-slave` mode).
- Détection du fichier récemment ouvert ou en lecture dans PulseAudio.
- Intégration Deezer via API ou WebSocket (pour usage navigateur).
