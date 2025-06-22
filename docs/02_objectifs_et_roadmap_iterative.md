#### Objectif final
- Afficher les paroles synchronisées (en romaji) **en temps réel** pendant la lecture de la chanson.

#### Roadmap itérative
1. ✅ Récupération des tags ID3 d’un fichier MP3 (`title`, `artist`).
2. ✅ Recherche automatique des paroles en romaji via scraping Google + sites spécialisés.
3. ✅ Scraping avancé (avec Selenium furtif pour contourner les protections JS).
4. ✅ CLI utilisable avec un fichier `.mp3`.
5. 🔜 Système de **cache local** pour éviter les recherches répétées.
6. 🔜 Affichage **synchronisé** avec l’audio (`mplayer` dans un premier temps).
7. 🔜 Overlay GUI ou terminal enrichi (type `curses` / `rich`).
8. 🔜 Extension Deezer (via navigateur, API, ou détection de chanson active).
