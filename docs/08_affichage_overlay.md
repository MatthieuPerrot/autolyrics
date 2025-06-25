# 08 - Étude de l'affichage des paroles en Overlay avec MPV

L'objectif est d'afficher les paroles synchronisées (fichiers `.srt` générés et post-traités) comme un overlay par-dessus les autres applications, en utilisant `mpv` comme moteur d'affichage sous Linux (X11).

## Approches envisagées

### 1. Utilisation des options de ligne de commande de `mpv`

`mpv` offre de nombreuses options pour contrôler l'apparence et le comportement de sa fenêtre. Pour un mode overlay, les options suivantes sont particulièrement pertinentes :

*   **Fenêtre sans décorations et positionnement :**
    *   `--no-border`: Supprime les bordures et la barre de titre de la fenêtre.
    *   `--geometry=<W>x<H>+<X>+<Y>`: Permet de définir la taille (Largeur, Hauteur) et la position (X, Y) de la fenêtre. Des pourcentages par rapport à la taille de l'écran peuvent être utilisés (ex: `--geometry=80%x10%+10%-5%` pour un bandeau en bas).
    *   `--autofit=<W>x<H>`: Peut aussi aider à contrôler la taille maximale.

*   **Comportement de la fenêtre :**
    *   `--ontop`: Rend la fenêtre toujours visible au-dessus des autres. Essentiel pour un overlay.
    *   `--window-dragging=no`: Empêche le déplacement de la fenêtre à la souris.
    *   `--focus-on=never` (macOS principalement) : Pourrait aider à ce que l'overlay ne vole pas le focus.
    *   `--input-cursor-passthrough=yes`: **Très important.** Permet aux clics de souris de "traverser" la fenêtre `mpv`, rendant l'overlay non interactif aux clics.

*   **Lecture audio uniquement avec affichage des sous-titres :**
    *   `--no-video` ou `--vid=no`: Ne décode/n'affiche pas de flux vidéo.
    *   `--force-window=yes`: Force la création d'une fenêtre même sans vidéo, nécessaire pour afficher les sous-titres.
    *   `--audio-display=no`: Empêche l'affichage de pochettes d'album ou de visualisations pour les fichiers audio.

*   **Affichage des sous-titres (SRT) :**
    *   `--sub-file=/chemin/vers/paroles.srt`: Charge le fichier de paroles.
    *   Options de style : `--sub-font-size`, `--sub-color`, `--sub-align-y`, `--sub-margin-y`, etc., pour personnaliser l'apparence des paroles. Les balises `<font color="...">` dans le SRT devraient être respectées par `mpv`.

*   **Transparence (le point le plus délicat) :**
    *   `mpv` ne semble pas avoir d'option de ligne de commande directe pour rendre le *fond de sa fenêtre* transparent tout en gardant le texte opaque, surtout en l'absence de flux vidéo avec canal alpha.
    *   L'option `--background=<none|color>` contrôle le fond si la *source* a un canal alpha.
    *   La transparence de la fenêtre dépendra probablement du **gestionnaire de fenêtres X11 et d'un compositeur** (ex: `picom`, `compton`, ou ceux intégrés à des environnements de bureau comme KWin, Mutter).
        *   Ces compositeurs peuvent être configurés pour appliquer une opacité (ou une transparence pour les régions non dessinées par l'application) à des fenêtres spécifiques, identifiées par leur classe (`mpv`), leur titre (qu'on peut fixer avec `--title`), ou leur ID.
        *   Par exemple, avec `picom`, on pourrait ajouter une règle dans `picom.conf` :
            `opacity-rule = [ "90:class_g = 'mpv' && name = 'MPV_LYRICS_OVERLAY'" ];` (pour 90% d'opacité).
            Pour une vraie transparence du fond, il faudrait que `mpv` ne dessine "rien" en fond et que le compositeur le gère.

**Exemple de commande `mpv` pour un début d'overlay :**
```bash
mpv --title="MPV_LYRICS_OVERLAY" \
    --no-border --ontop \
    --geometry=80%x10%+10%-5% \
    --window-dragging=no --input-cursor-passthrough=yes \
    --no-video --force-window=yes --audio-display=no \
    --sub-file=paroles.srt \
    --sub-font-size=48 --sub-color="#FFFFFF" --sub-border-color="#000000" --sub-border-size=1.5 \
    --sub-align-y=bottom --sub-margin-y=20 \
    musique.mp3
```
Cette commande crée une fenêtre sans bordure, toujours au-dessus, positionnée en bas, qui ne devrait pas réagir aux clics. La transparence du fond de cette fenêtre pour que seul le texte soit visible dépendra du compositeur X11.

### 2. Scripts Lua pour `mpv`

*   **Capacités :** Les scripts Lua peuvent contrôler finement l'OSD de `mpv` et l'affichage de texte via la commande `osd-overlay` qui supporte le formatage ASS. Un script pourrait parser le fichier SRT et afficher les paroles ligne par ligne (ou mot par mot) en utilisant des événements ASS dynamiquement créés.
*   **Limites pour l'overlay :** Les scripts Lua opèrent *à l'intérieur* de la fenêtre `mpv`. Ils ne peuvent pas rendre la fenêtre `mpv` elle-même transparente ou sans bordure si `mpv` ou le système ne le permettent pas via les options de ligne de commande ou la configuration du compositeur.
*   **Utilité :** Si les options SRT standard de `mpv` ne sont pas suffisantes pour l'affichage désiré (par exemple, effets de karaoké plus complexes que la simple coloration de mot, ou gestion fine de l'apparition/disparition des lignes), un script Lua serait la solution pour un rendu personnalisé *dans* la fenêtre `mpv`.

### 3. Outils externes (`wmctrl`, `xdotool`)

*   Ces outils en ligne de commande pour X11 permettent de manipuler les fenêtres existantes.
*   **`wmctrl` :**
    *   Peut identifier une fenêtre par son titre (ex: `wmctrl -l | grep "MPV_LYRICS_OVERLAY"`).
    *   Peut la rendre "toujours au-dessus" : `wmctrl -i -r $WINDOW_ID -b add,above`.
    *   Peut changer sa géométrie : `wmctrl -i -r $WINDOW_ID -e <G,X,Y,W,H>`.
    *   Ne gère pas directement la transparence fine (fond transparent, texte opaque).
*   **`xdotool` :**
    *   Peut aussi identifier et manipuler la géométrie des fenêtres.
    *   Pour la transparence, il faudrait l'utiliser pour appeler `xprop` afin de modifier la propriété `_NET_WM_WINDOW_OPACITY`, ce qui règle l'opacité globale de la fenêtre et nécessite un compositeur.
*   **Utilité :** Peuvent être utiles pour forcer certains états de la fenêtre `mpv` après son lancement si les options de ligne de commande de `mpv` ne sont pas prises en compte par le gestionnaire de fenêtres.

## Conclusion sur l'approche Overlay avec `mpv`

La solution la plus intégrée et prometteuse semble être :
1.  **Lancer `mpv`** avec les options de ligne de commande appropriées pour configurer la fenêtre (sans bordure, toujours au-dessus, position/taille, pas de vidéo, chargement du SRT, etc.) et surtout `input-cursor-passthrough=yes`.
2.  **Utiliser un gestionnaire de fenêtres composite X11** (comme `picom`) et le configurer spécifiquement pour rendre la fenêtre `mpv` (identifiée par son titre ou sa classe) avec un fond transparent, ou avec le niveau d'opacité souhaité. C'est cette étape qui gérera la véritable "transparence d'overlay".
3.  Les paroles (fichier `.srt` post-traité avec les balises `<font>` pour la coloration) seront affichées par `mpv` au sein de cette fenêtre.

Si un contrôle plus fin sur l'affichage des paroles (animations, transitions non supportées par le rendu SRT de base de `mpv`) est nécessaire, un script Lua pour `mpv` pourrait être développé pour prendre en charge le rendu des paroles via l'OSD en format ASS. Cependant, cela ajoute de la complexité et n'est peut-être pas nécessaire si l'affichage SRT actuel avec `mpv` est jugé suffisant.

Le développement d'un afficheur Python entièrement séparé (avec PyQt, Kivy) reste une option plus lourde si l'approche `mpv` + compositeur ne donne pas les résultats escomptés en termes de transparence ou de flexibilité d'affichage.
