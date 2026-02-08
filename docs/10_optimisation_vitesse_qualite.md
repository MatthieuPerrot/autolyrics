# Optimisation vitesse & qualite — Panorama des fonctionnalites

## Contexte

Le systeme de fetching de lyrics repose sur un orchestrateur a 3 phases (REQUESTS, SELENIUM, CHROME_FETCHER) et un registry de 6 sources avec des quality ratings statiques. Les bases architecturales sont en place (fetch/parse separation, source registry, escalade par fetcher).

Ce document recense les fonctionnalites d'optimisation identifiees, leurs prerequis, et le graphe de dependances complet.

### Etat actuel

| Composant | Etat |
|-----------|------|
| Source registry (6 sources, quality ratings, fetcher capabilities) | OK |
| Three-phase orchestrator (REQUESTS -> SELENIUM -> CHROME_FETCHER) | OK |
| Fetch/parse separation (`search_*`, `parse_*` purs) | OK |
| Logs par tentative (stdout uniquement) | OK, mais ephemere |

### Ce qui manque

- Les logs sont des `print()` — pas de donnee structuree reutilisable
- L'ordonnancement est statique (`romaji_quality` fixe dans le registry)
- Les recherches et les fetches sont sequentiels
- Aucune evaluation de la qualite du resultat obtenu (au-dela du binaire `is_likely_romaji`)
- Pas de persistance (stats, cache, historique)

---

## Prerequis transverses (briques structurelles)

L'analyse des features fait emerger 5 briques fondamentales reutilisees par plusieurs fonctionnalites.

### P1. Event model structure

Un modele de donnees pour les evenements d'un run : recherche, tentative de fetch, resultat de parse. Aujourd'hui ces informations n'existent que comme `print()` formates.

**Deux types d'evenements :**

```
SearchEvent:
  source, query, duration_s, num_urls_found, timestamp

FetchEvent:
  source, fetcher, url, phase, duration_s,
  http_status, fetch_ok, parse_ok, lyrics_len, timestamp
```

**Consommateurs :** F1 (run summary), F2 (JSON logs), F3 (stats store), F4 (stats-driven ordering), F5 (circuit breaker)

### P2. Persistent storage

Convention de stockage persistant et I/O standardise.

- Emplacement : `~/.autolyrics/` (hors du repo)
- Sous-repertoires : `logs/` (`.jsonl`), `stats/` (`.json`), `cache/` (`.json`)

**Consommateurs :** F2 (JSON logs), F3 (stats store), F5 (circuit breaker), F8 (search cache)

### P3. Concurrency infrastructure

Pattern `concurrent.futures.ThreadPoolExecutor` avec collecte de resultats et timeout. Meme pattern reutilisable pour la parallelisation des recherches et des fetches.

**Considerations :**
- Les `search_*` sont des fonctions pures et independantes, directement parallelisables
- Les fetches partagent potentiellement les memes backends de recherche (risque de rate-limiting DuckDuckGo si trop de requetes simultanees)
- Le lifecycle des fetchers (SeleniumFetcher, ChromeFetcher) doit etre gere en dehors du pool de threads

**Consommateurs :** F6 (parallel search), F7 (parallel fetch), F9 (multi-result comparison)

### P4. Result quality evaluator

Fonction `evaluate_lyrics(text, source_quality) -> float [0.0-1.0]` qui evalue la qualite d'un resultat obtenu.

**Etend** `is_likely_romaji` (binaire) **vers un score gradue.** Facteurs :

| Facteur | Signal | Poids |
|---------|--------|-------|
| Confiance romaji | ratio de mots romaji-like vs anglais/japonais | fort |
| Longueur / completude | nb de lignes, nb de caracteres (une chanson typique fait 20-60 lignes) | moyen |
| Structure | presence de strophes (sauts de ligne), pas un mur de texte | faible |
| Qualite source | `romaji_quality` du registry (1-5, normalise) | moyen |

**Consommateurs :** F7 (parallel fetch — selection du meilleur resultat), F9 (multi-result comparison — seuil "suffisant"), F4 (ponderation par qualite reelle, optionnel)

**Note :** Sans cette brique, le fetch parallele ne peut faire que "premier succes gagne" (risque de retenir un resultat mediocre). Et le multi-result comparison n'a aucun sens.

### P5. Time budget

Un `deadline` global (timestamp absolu) propage a travers les phases, avec abandon propre au-dela.

- Chaque phase verifie `time.time() < deadline` avant chaque tentative
- Le budget restant est passe aux fetchers comme `timeout`
- Permet de borner le pire cas (ex: 90s max)

**Consommateurs :** F7 (parallel fetch), F9 (multi-result comparison), F10 (global timeout)

---

## Features

### F1. Run summary

Tableau recapitulatif affiche en fin de run.

```
┌──────────────────┬──────────┬────────┬─────────┬──────────┐
│ Source           │ Fetcher  │ Duree  │ Statut  │ Phase    │
├──────────────────┼──────────┼────────┼─────────┼──────────┤
│ lyrical_nonsense │ requests │  1.2s  │ parse ✗ │ Phase 1  │
│ animelyrics      │ requests │  0.8s  │ 403     │ Phase 1  │
│ animelyrics      │ selenium │  6.3s  │ OK ✓    │ Phase 2  │
└──────────────────┴──────────┴────────┴─────────┴──────────┘
Total: 8.3s | Resultat: animelyrics (Phase 2, selenium)
```

| | |
|---|---|
| **Prerequis briques** | P1 (event model) |
| **Depend de features** | aucune |
| **Debloque** | aucune |
| **Complexite** | faible |
| **Impact vitesse** | — (visibilite, pas d'acceleration) |
| **Impact qualite** | — |

### F2. Structured JSON logging

Ecriture de chaque evenement (search + fetch) dans un fichier `.jsonl` persistant. Un fichier par jour ou par run.

| | |
|---|---|
| **Prerequis briques** | P1 (event model), P2 (persistent storage) |
| **Depend de features** | aucune |
| **Debloque** | F3 (stats store — les `.jsonl` sont l'input de l'agregation) |
| **Complexite** | faible |
| **Impact vitesse** | — |
| **Impact qualite** | — (mais fondation pour l'intelligence data-driven) |

### F3. Persistent stats store

Agregation des logs en metriques par source : taux de succes, latence moyenne, taux de 403, derniere date de succes.

Fichier `~/.autolyrics/stats/source_stats.json` mis a jour apres chaque run.

| | |
|---|---|
| **Prerequis briques** | P1 (event model), P2 (persistent storage) |
| **Depend de features** | F2 (les logs jsonl sont la source de verite) |
| **Debloque** | F4 (stats-driven ordering), F5 (circuit breaker) |
| **Complexite** | faible |
| **Impact vitesse** | — |
| **Impact qualite** | — (mais fondation pour F4 et F5) |

### F4. Stats-driven ordering

Reordonnancement dynamique des sources au sein de chaque phase, base sur les stats historiques.

Score de tri : `success_rate * source_quality` (ou `success_rate * avg_result_quality` si P4 est disponible) au lieu du `romaji_quality` statique actuel.

| | |
|---|---|
| **Prerequis briques** | (transitifs via F3 : P1, P2) |
| **Depend de features** | **F3** (hard — a besoin de stats historiques pour calculer le score) |
| **Debloque** | aucune |
| **Complexite** | moyenne |
| **Impact vitesse** | ++ (les sources qui marchent le plus souvent sont essayees en premier) |
| **Impact qualite** | ++ (idem) |
| **Enrichi par** | P4 (quality evaluator — ponderation par qualite reelle du resultat, pas seulement succes/echec) |

### F5. Circuit breaker

Desactivation temporaire d'une source apres N echecs consecutifs. Evite de perdre du temps sur des sources mortes.

| | |
|---|---|
| **Prerequis briques** | P2 (persistent storage) |
| **Depend de features** | **F3** (idealement) ou P2 seul (version simple : fichier `failures.json` avec compteur par source) |
| **Debloque** | aucune |
| **Complexite** | faible |
| **Impact vitesse** | + (evite les tentatives inutiles) |
| **Impact qualite** | — |
| **Variantes** | *Simple* : compteur d'echecs consecutifs par source, seuil fixe. *Riche* : lit les stats agregees de F3. |

### F6. Parallel search

Lancement des 6 `search_*` en parallele via `ThreadPoolExecutor`. Gain potentiel : ~2s au lieu de ~12s sequentiel.

| | |
|---|---|
| **Prerequis briques** | P3 (concurrency) |
| **Depend de features** | aucune |
| **Debloque** | F7 (les URLs de search sont disponibles plus tot) |
| **Complexite** | faible |
| **Impact vitesse** | +++ (bottleneck actuel : 6 recherches sequentielles) |
| **Impact qualite** | — |
| **Risques** | Rate-limiting DuckDuckGo si 6 requetes simultanees. Mitigation : limiter le pool a 3 workers. |

### F7. Parallel Phase 1 fetch

Lancement des fetches REQUESTS en parallele au sein de la Phase 1, avec selection du meilleur resultat.

| | |
|---|---|
| **Prerequis briques** | P3 (concurrency), **P4 (quality evaluator)**, P5 (time budget) |
| **Depend de features** | beneficie de F6 (URLs disponibles plus tot) |
| **Debloque** | F9 (c'est le mecanisme sous-jacent du multi-result) |
| **Complexite** | moyenne |
| **Impact vitesse** | ++ (toutes les sources en parallele, premiere reponse suffisante acceptee) |
| **Impact qualite** | ++ (possibilite de choisir le meilleur resultat, pas juste le premier) |

**Strategie de selection :**
- Sans P4 : "premier succes gagne" — simple mais risque de retenir un resultat mediocre (ex: mojim quality=1 repond avant lyrical_nonsense quality=5)
- Avec P4 : "premier succes *suffisant* gagne" — accepte immediatement si `score >= seuil`, sinon attend d'autres resultats dans le budget temps

### F8. Search result caching

Cache persistant `(title_normalise, artists_normalises) -> {source: [urls], timestamp}`.

Evite de relancer les recherches Google/DuckDuckGo pour une chanson deja cherchee. Invalidation par TTL (ex: 7 jours).

| | |
|---|---|
| **Prerequis briques** | P2 (persistent storage) |
| **Depend de features** | aucune |
| **Debloque** | aucune |
| **Complexite** | faible |
| **Impact vitesse** | ++ (elimine la phase de search sur les re-runs) |
| **Impact qualite** | — |
| **Risques** | Cache invalide si une source ajoute la chanson apres la premiere recherche. Mitigation : TTL + option `--no-cache`. |

### F9. Multi-result comparison

Au lieu de s'arreter au premier succes, collecter plusieurs resultats dans un budget temps et choisir le meilleur.

| | |
|---|---|
| **Prerequis briques** | **P4 (quality evaluator)**, P3 (concurrency), P5 (time budget) |
| **Depend de features** | **F7** (parallel fetch est le mecanisme), **P4 est le hard prerequisite** |
| **Debloque** | aucune |
| **Complexite** | moyenne |
| **Impact vitesse** | − (ralentit volontairement le happy path) |
| **Impact qualite** | +++ |

**Logique :**
1. Recevoir un resultat de source X
2. Evaluer avec P4 → score
3. Si `score >= seuil_suffisant` → accepter immediatement (short-circuit)
4. Si `score < seuil_suffisant` → stocker, attendre d'autres resultats jusqu'au budget temps
5. A expiration du budget → retourner le meilleur parmi ceux collectes

**Sans P4, cette feature n'a aucun sens** — c'est la brique d'evaluation qui determine si un resultat est "suffisant" ou s'il faut continuer a chercher.

### F10. Global timeout

Budget temps global (ex: 90s) avec abandon propre. Borne le pire cas (aujourd'hui potentiellement 60s+ sur ChromeFetcher seul).

| | |
|---|---|
| **Prerequis briques** | P5 (time budget) |
| **Depend de features** | aucune |
| **Debloque** | aucune (mais P5 est reutilise par F7 et F9) |
| **Complexite** | faible |
| **Impact vitesse** | ++ (borne le pire cas) |
| **Impact qualite** | — |

---

## Graphe de dependances

### Chaine "Data-driven" (logging -> stats -> intelligence)

```
P1 (event model)
 │
 ├──► F1 (run summary)              [P1]
 │
 └──► F2 (JSON logs)                [P1 + P2]
       │
       └──► F3 (stats store)        [P1 + P2 + F2]
             │
             ├──► F4 (ordering)     [F3, enrichi par P4]
             │
             └──► F5 (circuit brk)  [F3 ou P2 seul]

P2 (persistent storage)
 │
 ├──► F2, F3, F5 (voir ci-dessus)
 │
 └──► F8 (search cache)             [P2]
```

### Chaine "Speed" (parallelisme -> qualite runtime)

```
P3 (concurrency)
 │
 ├──► F6 (parallel search)          [P3]
 │
 └──► F7 (parallel fetch)           [P3 + P4 + P5]
       │
       └──► F9 (multi-result)       [F7 + P4 + P5]

P5 (time budget)
 │
 ├──► F7, F9 (voir ci-dessus)
 │
 └──► F10 (global timeout)          [P5]
```

### Pont entre les deux chaines

```
P4 (quality evaluator)
 │
 ├──► F7  (selection du meilleur resultat parallele)
 ├──► F9  (seuil "suffisant" pour le multi-result)
 └──► F4  (ponderation par qualite reelle, optionnel)
```

### Vue consolidee des dependances

```
Brique/Feature  │ Depend de
────────────────┼─────────────────────────────────
P1              │ —
P2              │ —
P3              │ —
P4              │ —  (etend is_likely_romaji existant)
P5              │ —
────────────────┼─────────────────────────────────
F1  run summary │ P1
F2  JSON logs   │ P1, P2
F3  stats store │ P1, P2, F2
F4  ordering    │ F3  (optionnel: P4)
F5  circuit brk │ P2  (enrichi par F3)
F6  par. search │ P3
F7  par. fetch  │ P3, P4, P5
F8  cache       │ P2
F9  multi-res.  │ P3, P4, P5, F7
F10 timeout     │ P5
```

---

## Roadmap recommandee

### Tier 1 — Fondations et quick wins

Objectif : poser les briques transverses et recolter les gains immediats.

| Ordre | Element | Justification |
|:-----:|---------|---------------|
| 1 | **P1** (event model) | Debloque toute la chaine data-driven (F1, F2, F3) |
| 2 | **P2** (persistent storage) | Debloque F2, F8, F5 |
| 3 | **F1** (run summary) | Quick win : visibilite immediate, ne depend que de P1 |
| 4 | **F2** (JSON logs) | Fondation pour F3 → F4/F5 |
| 5 | **P3** (concurrency) | Debloque toute la chaine speed (F6, F7) |
| 6 | **F6** (parallel search) | Quick win a fort impact (~10s gagnes par run) |

### Tier 2 — Intelligence data-driven

Objectif : exploiter les donnees collectees pour des decisions automatiques.

| Ordre | Element | Justification |
|:-----:|---------|---------------|
| 7 | **F3** (stats store) | Fondation pour F4, F5 |
| 8 | **F5** (circuit breaker) | Quick win defensif — evite les sources mortes |
| 9 | **F4** (ordering dynamique) | Les sources qui marchent le plus passent devant |
| 10 | **F8** (search cache) | Independant, elimine le search sur re-runs |

### Tier 3 — Optimisations avancees

Objectif : maximiser la qualite du resultat et borner le pire cas.

| Ordre | Element | Justification |
|:-----:|---------|---------------|
| 11 | **P4** (quality evaluator) | Hard prerequisite de F7 "smart" et F9 |
| 12 | **P5** (time budget) | Hard prerequisite de F7, F9, F10 |
| 13 | **F10** (global timeout) | Borne le pire cas, simple une fois P5 en place |
| 14 | **F7** (parallel fetch) | Acceleration Phase 1 + selection intelligente |
| 15 | **F9** (multi-result) | Le "graal" qualite — ne declenche que si premier resultat insuffisant |
