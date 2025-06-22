#### Sources de lyrics utilisées (dans l’ordre de priorité)
1. **animelyrics.com**
2. **lyrical-nonsense.com**
3. **genius.com** (vérifie l’absence de "To be transcribed")
4. **j-lyric.net** (en test)
5. **nautiljon.com** (fonctionne via Selenium + contournement des protections JS)

#### Mécanisme de recherche
- Recherche Google ciblée :
  ```
  site:<source> "romaji lyrics" "<artist>" "<title>"
  ```
- Fallback automatique si une source échoue.
- Parsing HTML ou via Selenium en fonction du site.

#### Limites actuelles
- Certains titres peuvent être absents ou mal nommés (problème d’alias, transcription, etc.).
- Pas encore de vérification croisée entre les résultats.

#### Propositions d’amélioration futures
- Détection automatique de la langue du titre pour adapter les sources.
- Intégration de cache local (`lyrics_cache/` ?).
- Requête Google étendue à d’autres sources si toutes échouent.
