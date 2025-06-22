### 05_affichage_lyrics.md

#### État actuel
- Les paroles sont affichées en bloc dans le terminal après récupération.

#### Besoin identifié
- Afficher les paroles **synchronisées** avec l’audio en cours.
- Priorité : lecture locale via `mplayer`.

#### Objectifs futurs
- Lire les timestamps s'ils sont disponibles (fichiers LRC, ou alignement heuristique ?).
- Si pas de timestamps : découpage automatique en lignes + scroll progressif synchronisé avec la durée moyenne d’une ligne.
- Options d’affichage envisagées :
  - `rich` terminal UI (belle mise en page dans console).
  - GUI overlay (PyQt5, Tkinter, Zenity, etc.).
  - Intégration dans un `tmux` ou `conky`.

#### Propositions de prochaines étapes
- Prototype minimal : afficher une ligne toutes les N secondes en défilement.
- Synchronisation approximative avec la durée de la chanson (déduite de ffprobe ou tags).
- Test d’un affichage avec `rich.live.Live` ou `curses` pour première version console.
