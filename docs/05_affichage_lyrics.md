# 05 - Options d'affichage des paroles synchronisées

L'objectif est de trouver des solutions pour afficher les fichiers de paroles synchronisées (principalement au format `.lrc`, idéalement Enhanced LRC pour la mise en évidence mot à mot) avec un lecteur MP3 sur Ubuntu/Linux.

## 1. Utilisation de lecteurs de musique existants

Idéalement, un lecteur de musique existant devrait pouvoir lire le MP3 et afficher le fichier `.lrc` associé.

*   **Strawberry / Clementine:**
    *   **Description :** Lecteurs de musique populaires, bien fournis en fonctionnalités. Strawberry est un fork de Clementine.
    *   **Support LRC :** Généralement bon. Ils peuvent trouver et afficher des fichiers `.lrc` (nommés comme le fichier audio) et souvent télécharger des paroles.
    *   **Support Enhanced LRC (mot à mot) :** Probable, car ils visent une expérience complète. À vérifier en pratique, mais ce sont des candidats solides.
    *   **Avantages :** Solution intégrée, interface utilisateur graphique complète.
    *   **Inconvénients :** Dépend du niveau exact de support de l'Enhanced LRC pour la coloration mot à mot.

*   **VLC Media Player:**
    *   **Description :** Lecteur multimédia très polyvalent.
    *   **Support LRC :** Supporte le chargement de fichiers de sous-titres, y compris `.lrc` (généralement pour un affichage ligne par ligne).
    *   **Support Enhanced LRC (mot à mot) :** Probablement limité pour un affichage karaoké mot à mot. VLC est plus conçu pour des blocs de sous-titres.
    *   **Avantages :** Très répandu.
    *   **Inconvénients :** L'affichage karaoké avancé n'est pas sa fonction première.

*   **Audacious:**
    *   **Description :** Lecteur audio léger.
    *   **Support LRC :** Peut afficher des fichiers `.lrc` simples, often via des plugins (ex: LyricWiki).
    *   **Support Enhanced LRC (mot à mot) :** Moins probable nativement.
    *   **Avantages :** Léger.
    *   **Inconvénients :** Support potentiellement basique.

*   **Rhythmbox (GNOME), Elisa (KDE), et autres lecteurs de bureau:**
    *   **Description :** Lecteurs intégrés aux environnements de bureau.
    *   **Support LRC :** Peut être présent, souvent de manière basique (ligne par ligne) et parfois via des plugins tiers dont la maintenance et les fonctionnalités peuvent varier.
    *   **Support Enhanced LRC (mot à mot) :** Peu probable pour la plupart.

*   **MPV Player:**
    *   **Description :** Un lecteur vidéo et audio en ligne de commande, fork de mplayer, très puissant et configurable.
    *   **Support LRC :** Pas de support direct et simple pour LRC comme format de paroles principal. Cependant, MPV a un système de scripting Lua très puissant. Il serait possible d'écrire un script Lua pour parser un fichier `.lrc` (y compris Enhanced LRC) et afficher les paroles en surimpression (overlay) sur la vidéo (ou une fenêtre noire si c'est juste de l'audio). Il supporte nativement les formats de sous-titres vidéo comme `.ass` et `.srt`.
    *   **Avantages :** Extrêmement flexible, contrôlable par script, haute qualité. Si l'on convertit le `.lrc` en `.ass`, MPV l'affichera parfaitement.
    *   **Inconvénients :** Nécessite du scripting pour une solution LRC directe, ou une étape de conversion en `.ass`.

*   **Mplayer (lecteur cible initial) :**
    *   **Description :** Lecteur en ligne de commande.
    *   **Support LRC :** Très limité, voire inexistant pour un affichage synchronisé direct. `mplayer` est souvent utilisé comme backend pour des frontends plus évolués. Un script externe pourrait écouter `mplayer` et afficher les paroles, mais la synchronisation serait un défi.

*   **Logiciels de Karaoké dédiés:**
    *   **Exemples :** UltraStar Deluxe, Performous, Vocaluxe (open-source); Kanto Karaoke (commercial).
    *   **Support LRC/ASS :** Généralement excellent, car c'est leur fonction principale. Ils supportent souvent la coloration mot à mot.
    *   **Avantages :** Expérience karaoké optimale.
    *   **Inconvénients :** Peuvent être des applications plus lourdes (jeux) ou commerciales. L'intégration dans un workflow "simple lecteur MP3" peut être moins directe.

## 2. Développement d'un afficheur personnalisé en Python

Si les lecteurs existants ne suffisent pas ou pour un contrôle total (notamment pour un overlay), une application Python peut être développée.

*   **Pygame:**
    *   **Description :** Bibliothèque pour le développement de jeux, mais utile pour l'audio et les graphismes simples.
    *   **Fonctionnalités :** Peut lire l'audio, gérer le temps, et afficher du texte.
    *   **Avantages :** Déjà introduite dans le projet (`sync_lyrics.py`), multiplateforme, contrôle total.
    *   **Inconvénients :** Nécessite de coder toute la logique d'affichage, de parsing LRC, de timing et de mise en évidence mot à mot. Le rendu de texte est basique par défaut.

*   **Frameworks GUI (Tkinter, PyQt, Kivy):**
    *   **Description :** Bibliothèques pour créer des interfaces graphiques plus complètes.
    *   **PyQt/Kivy :** Plus modernes, supportent mieux le stylage avancé, les animations, la transparence pour des overlays.
    *   **Avantages :** Composants riches, meilleur rendu, gestionnaire d'événements.
    *   **Inconvénients :** Plus complexes à prendre en main si l'on n'est pas familier.

*   **Bibliothèques de Terminal (Rich, curses):**
    *   **Description :** Pour un affichage dans le terminal.
    *   **Rich :** Permet un affichage très stylé (couleurs, etc.) dans les terminaux modernes.
    *   **Avantages :** Léger, pas de dépendance à un serveur graphique.
    *   **Inconvénients :** Limité aux capacités du terminal, pas d'overlay sur d'autres applications.

## 3. Affichage en Overlay

L'objectif d'afficher les paroles en surimpression par-dessus d'autres applications est un défi technique :
*   Cela nécessite généralement de créer une fenêtre sans bordures, toujours au-dessus, et potentiellement transparente.
*   Des bibliothèques comme **PyQt** ou **Kivy** sont plus adaptées pour cela, en utilisant les fonctionnalités spécifiques du système d'exploitation pour gérer le comportement de la fenêtre.
*   Sur Linux, des outils comme `conky` font de l'overlay, mais une intégration dynamique serait complexe. Des solutions basées sur X11 (ou Wayland) directes sont possibles mais très bas niveau.

## Conclusion et Recommandations

*   **Pour l'utilisateur final (Ubuntu) :**
    1.  Tester **Strawberry** ou **Clementine** avec des fichiers Enhanced LRC. Ce sont les options les plus prometteuses pour une solution "out-of-the-box".
    2.  Si une conversion en format `.ass` (Advanced SubStation Alpha) est envisageable, **MPV** devient un excellent choix pour un affichage de haute qualité et personnalisable.
    3.  Explorer des lecteurs de karaoké dédiés comme **Performous** ou **UltraStar Deluxe** si une expérience "jeu de karaoké" est souhaitée.

*   **Pour un développement personnalisé (si nécessaire) :**
    1.  **Pygame** peut servir pour un prototype simple d'affichage synchronisé.
    2.  Pour un affichage plus riche ou un mode overlay, **PyQt** ou **Kivy** sont des pistes sérieuses.

*   **Concernant `mplayer` :** Une intégration directe pour l'affichage de paroles synchronisées est peu probable sans un frontend ou un wrapper complexe. Il est préférable de se tourner vers des lecteurs avec un meilleur support natif ou de scripting (comme MPV).

Pour l'instant, la priorité est de générer correctement des fichiers `.lrc` (Enhanced). L'affichage peut ensuite être délégué à un lecteur compatible. Si l'objectif d'overlay devient prioritaire, un développement spécifique avec PyQt/Kivy sera nécessaire.
