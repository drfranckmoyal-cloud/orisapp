# Marque Oris — ligne de son, profil de dent

Le geste : une **onde sonore** dont les montées et les descentes composent le profil
d'une **molaire**. Le haut donne deux cuspides séparées d'un sillon, le bas deux
racines. De loin on lit un niveau sonore, de près une dent — jamais de dent dessinée
littéralement.

| Fichier | Usage |
|---|---|
| `oris-symbole-barres.svg` | **Symbole principal.** Tient jusqu'à 20 px. |
| `oris-symbole-ligne.svg` | Tracé continu, plus fin. Grands formats seulement. |
| `oris-symbole-creme.svg` | Le symbole sur fonds verts (barre de menu). |
| `oris-logo-horizontal.svg` | En-tête de site, papier à en-tête. |
| `oris-logo-vertical.svg` | Écran d'accueil, page de garde. |
| `oris-logo-blanc.svg` | Fonds sombres. |
| `oris-logo-monochrome.svg` | Tampon, fax, impression une encre. |
| `oris-icone-app.svg` | Icône d'application (512 px, coins arrondis). |
| `oris-favicon.svg` | Onglet : trois barres, les deux cuspides et le sillon. |
| `planche.html` | La planche à ouvrir pour juger l'ensemble. |
| `slogans.html` | Les deux slogans finalistes, en situation. |
| `polices/Fraunces.ttf` | La police du nom, sous licence SIL OFL (`OFL.txt`). Elle ne sert qu'à **produire** les fichiers : les SVG et les PNG n'en dépendent plus. |
| `png/` | **Tous les formats en PNG** — symbole (vert, crème, encre), icône d'application, favicon, de 16 à 1024 px. Régénérés par `python3 scripts/export_marque.py`. |

## Règles

- **Jamais moins de 20 px** pour la version à cinq barres : en dessous, elles se
  referment. Utiliser `oris-favicon.svg`.
- Le symbole se décline en **une seule couleur** : vert `#14533B`, crème `#F6F3EE`
  sur fonds verts, encre `#1C1A17` en monochrome. Pas de dégradé, sauf sur l'icône
  d'application.
- **Ne jamais étirer** : le rapport des barres porte le sens (cuspides, sillon,
  racines).
- Marge de protection autour du symbole : la largeur d'une barre.

## Polices

- **Manrope** pour l'interface.
- **Fraunces** (600) pour le nom « Oris ».

## Le nom est vectorisé

Le mot « Oris » n'est plus du texte : c'est un tracé, composé en **Fraunces 600,
taille optique 48, axe WONK désactivé**, avec le crénage de la police. Les
verrouillages SVG et PNG ne dépendent donc d'aucune police installée — ils
s'impriment.

Pour recomposer le nom (changement de police ou de graisse) :

```
pip install fonttools
python3 scripts/vectoriser_nom.py   # réécrit les SVG
python3 scripts/export_marque.py    # réécrit les PNG
```

`oris-mot.txt` contient le tracé seul, pour le réemployer ailleurs.
