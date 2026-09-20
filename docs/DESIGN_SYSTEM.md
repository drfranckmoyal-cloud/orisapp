# Design System — Oris

**Verrouillé le 20 septembre 2026.** Cette page remplace la première version bleue.
Référence vivante : `design/maquettes/4b-praticien-affine.html`.

## Idée de marque

**Vous soignez. Oris documente.**

Le texte de référence et le second slogan en balance sont dans
`docs/POSITIONNEMENT.md`.

Oris doit se tenir comme un cabinet établi : calme, précis, lisible debout à un
mètre, et lisible aussi par le patient assis en face. Surtout pas « chatbot », pas
« start-up tech ».

## Logo

Une **ligne de son dont les montées et descentes composent le profil d'une
molaire** : deux cuspides séparées d'un sillon en haut, deux racines en bas. De
loin un niveau sonore, de près une dent. **Jamais de dent dessinée littéralement.**

Pendant l'écoute, les cinq barres deviennent le niveau réel du micro : la marque
n'illustre pas le produit, elle en est l'instrument.

- Fichiers vectoriels : `design/marque/*.svg`
- Fichiers PNG, toutes tailles : `design/marque/png/` — régénérés par
  `python3 scripts/export_marque.py`
- Planche à ouvrir pour juger : `design/marque/planche.html`
- Règles d'emploi : `design/marque/README.md`

**Jamais sous 20 px** pour la version à cinq barres : elles se referment. En
dessous, la version à trois barres (`favicon-*.png`).

## Couleurs

Source unique : `design/tokens.json` → `apps/web/src/app/tokens.css` et
`apps/ios/Oris/DesignSystem/Tokens.swift` (`scripts/generate_tokens.py`).

| Jeton | Hex | Emploi |
|---|---|---|
| `deepGreen` | `#0E3A29` | fond du menu, bord des boutons verts |
| `orisGreen` | `#14533B` | action principale, écoute, validé |
| `brightGreen` | `#1A6B4C` | haut du dégradé des boutons |
| `mistGreen` | `#E5EFE9` | fonds doux, pastilles validées |
| `sand` | `#F5F2EC` | fond de page |
| `cream` | `#F6F3EE` | plaque du logo, texte sur vert |
| `linen` | `#EBE5DB` | surfaces creusées (onglets) |
| `ink` | `#1A1815` | texte |
| `inkSoft` | `#544D44` | texte secondaire |
| `rule` | `#E3DCCF` | filets |
| `clay` | `#A8540A` | **à vérifier** — et rien d'autre |
| `danger` | `#9C2A1C` | alerte critique, échec |

Les écrans n'emploient **que** les noms sémantiques de `theme.css`
(`--accent`, `--encre`, `--attention`…), jamais une couleur brute.

## Typographie

- **Manrope** — toute l'interface. Chiffres tabulaires partout.
- **Fraunces** (600) — **le nom « Oris » uniquement**, et les titres qui portent la
  marque (le bouton « Commencer une consultation »). Classe `.marque-nom`.
- Chargées par `next/font/google`, auto-hébergées.

Échelle : 12 / 13,5 / 15,5 / 17,5 / 22 / 28 / 35 px. Graisses : 400, 600, 700, 800.

## Relief

Tout ce qui est posé sur la page porte **trois couches d'ombre plus un filet de
lumière**. Une ombre plate inventée sur place est un écart au système.

```css
--lumiere: inset 0 1px 0 rgb(255 255 255 / .9);
--relief:  0 1px 1px rgb(26 24 21 / .05),
           0 3px 6px -2px rgb(26 24 21 / .06),
           0 14px 30px -18px rgb(26 24 21 / .28);
```

Les surfaces claires portent un dégradé d'un souffle (`#fff` → `#fdfbf8`). Les
surfaces creusées (onglets, champs) portent une ombre **interne**.

Rayons : carte 20 px, bouton 13 px, grand bouton 16 px, pastille pleine.

**Marges intérieures.** Une carte a **24 px** de remplissage — le texte n'affleure
jamais le cadre. Deux variantes seulement :

- `serree` (16 px) pour les cartes secondaires ;
- `bords` (0) pour ce qui est **fait** pour toucher le cadre : un tableau
  d'informations, une liste dont les filets vont d'un bord à l'autre. Dans ce cas,
  ce sont les lignes qui portent la marge — jamais personne n'y échappe.

## Barre de gauche

- Bloc vert plein en dégradé (`--menu-haut` → `--menu-bas`), jamais transparente.
- **Le logo est une plaque crème posée dessus** — un objet, pas une inscription.
  Elle est cliquable et ramène à l'accueil.
- Les entrées portent des **pictogrammes** et **chacune sa propre surface** en
  relief. Jamais de puces : une liste à puces n'est pas une navigation.
- L'entrée active s'éclaire et porte un **repère argile sur le flanc gauche**.
- Le praticien se choisit en bas, dans un menu déroulant discret.

## Écrans

**Accueil** — un seul geste qui compte : le grand bouton vert *Commencer une
consultation*, avec le logo qui s'anime au survol. Puis la semaine en barres, la
saisie évitée (avec sa méthode de calcul affichée), ce qui attend, ce qu'Oris a
appris. Pas de « Bonjour Docteur ».

**Écoute active** — le symbole au centre dans un disque qui respire, ses barres au
niveau du micro. Chronomètre en 88 px. Micro, réseau, pause, marquer un point,
terminer. Panneau « ce qu'Oris entend » replié.

**Révision** — document à gauche sur une feuille à marge réglée, rail à onglets à
droite. Les mentions (« Rapporté par la patiente : ») en gris clair pour que le
clinique ressorte.

**Fiche patient** — un **cadre d'informations** en deux colonnes, pas des bulles
éparpillées. La note y est logée, discrète. L'historique en dessous, très lisible,
chaque ligne cliquable, avec un accès minuscule à la transcription brute. Pas de
plan de traitement : il appartient à la consultation.

## Ce qui n'est pas encore fait

- Le mot « Oris » des verrouillages n'est pas vectorisé : à faire avant toute
  impression. Les PNG n'exportent donc que le symbole.
- Le logo du cabinet ne remplace pas encore celui d'Oris sur les documents.
- Les écrans iPhone n'ont pas été repris sur cette direction.
