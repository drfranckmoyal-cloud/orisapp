# Audit produit et design — Oris

*Rédigé le 20 septembre 2026, après relecture intégrale du paquet de spécification et
examen du produit public d'Askara (benchmark de maturité, pas modèle à copier).*

---

## 1. Ce que j'ai lu, et ce que je n'avais pas lu

| Document | État |
|---|---|
| `ORIS_MASTER_SPEC_V1_2.md` (4 555 lignes) | Lu par sections, au fil des jalons. **Pas de bout en bout.** |
| `docs/UI_SCREEN_SPEC.md` (S01→S13) | **Lu en entier aujourd'hui seulement.** C'est la lacune principale : j'ai construit les écrans sans ce cahier sous les yeux. |
| `docs/DESIGN_SYSTEM.md`, `design/tokens.json` | Lus. Les jetons sont dans le code ; l'esprit ne l'est pas. |
| `assets/` (4 planches d'identité) | **Regardées aujourd'hui seulement.** |
| Autres `docs/`, `schemas/`, `corpus/`, `prompts/`, `evals/` | Lus et appliqués. |

C'est une erreur de méthode de ma part : j'ai traité le produit comme une chaîne
technique à faire fonctionner, et l'interface comme un moyen de la vérifier. D'où ce que
vous avez vu.

---

## 2. Verdict

**Ce qu'Oris est aujourd'hui** : une chaîne clinique solide (écoute → transcription →
faits → documents → correction → validation), mesurée et testée, **habillée d'une
interface de banc d'essai**. Sept écrans, aucun système de composants, aucun état vide
soigné, aucune continuité entre les consultations d'un même patient.

**Ce qu'Oris doit être** : un logiciel qu'un praticien ouvre le matin et garde ouvert.

L'écart n'est pas une affaire de couleurs. Il est structurel, et il tient en quatre
points.

### 2.1 Il n'existe pas de système de composants

Six fichiers de composants au total, dont deux utilitaires. Tout le reste est écrit
au cas par cas, avec des styles en ligne. Conséquence directe : chaque écran est
réinventé, rien n'est cohérent, et chaque ajout dégrade l'ensemble. **C'est la cause
racine de l'impression d'amateurisme.**

### 2.2 La typographie de la marque n'est pas chargée

`Inter` est déclaré dans la feuille de style, mais la police n'est **jamais chargée**.
L'application s'affiche donc dans la police système. La planche d'identité n'est pas
appliquée : elle est citée.

### 2.3 Il n'y a pas de continuité patient

Un patient est un nom dans une table. Pas de fiche, pas d'historique, pas de documents
rattachés, pas de plan de traitement suivi dans le temps. Une consultation est un
fichier isolé — exactement ce que vous ne voulez pas.

### 2.4 Le produit ne raconte rien

Pas de tableau de bord, pas d'« aujourd'hui », pas d'état de traitement, pas de
documents. L'utilisateur ne sait ni où il est, ni ce qui l'attend.

---

## 3. Audit écran par écran

Légende : **[O]** conforme · **[~]** partiel · **[X]** manquant ou défaillant.

### Accueil — attendu : tableau de bord clinique calme et utile
| Attendu (votre cahier + S01) | État |
|---|---|
| Consultations du jour | **[X]** absent |
| Dossiers à valider | **[~]** liste brute, sans compte ni tri |
| Consultations récemment terminées | **[X]** absent |
| Accès rapide à une nouvelle consultation | **[O]** présent depuis aujourd'hui |
| Salutation + nom du praticien | **[X]** « Bonjour » sans nom |

### Patients — attendu : vraie liste, vraie fiche
| Attendu | État |
|---|---|
| Recherche | **[X]** absente |
| Fiche patient | **[X]** inexistante (aucune page) |
| Consultations du patient | **[X]** absentes |
| Documents associés | **[X]** absents |
| Plans de traitement | **[X]** absents |
| Historique Oris | **[X]** absent |
| **Défaut constaté** | le nom s'affiche à l'envers : « d'essai Patient » |
| **Défaut constaté** | le formulaire de création occupe le haut de l'écran, avant la liste |

### Nouvelle consultation — attendu : patient → consultation → écoute
| Attendu | État |
|---|---|
| Choisir un patient **existant** | **[X]** régression que j'ai introduite ce matin : chaque essai crée un nouveau patient |
| Créer un patient à la volée | **[O]** |
| Un seul écran avant l'enregistrement (S03) | **[O]** |

### Consultation active — attendu : le cœur, spectaculaire mais discret
| Attendu (S04/S05) | État |
|---|---|
| Carte centrée, ~760 px | **[O]** |
| Minuteur à chiffres tabulaires | **[O]** |
| État micro, réseau, pause | **[O]** |
| Pulsation Oris Blue mesurée | **[~]** cercle statique, aucune animation |
| Visualisation audio très discrète | **[~]** barre de niveau brute |
| Transcription repliée à droite, fermée par défaut | **[X]** absente |
| Identité patient en haut | **[~]** nom seul, pas de carte |

### Traitement (S06) — attendu : étapes honnêtes
| Attendu | État |
|---|---|
| « Oris prépare le dossier… » + étapes réelles | **[X]** **écran absent** : la page se fige puis bascule. C'est le moment le plus fragile du produit, et il n'existe pas. |

### Revue (S07/S08) — attendu : environnement de révision
| Attendu | État |
|---|---|
| Grille 65/35 | **[O]** |
| Onglets du rail droit (À vérifier / Données / Historique) | **[X]** quatre cartes empilées à la place |
| Provenance d'une phrase | **[O]** fonctionne, et c'est une vraie force |
| Faits cliniques en français | **[X]** affichés avec leur code technique (`cold_sensitivity : …`) |
| Correction vocale | **[~]** présente, mais noyée en bas du rail |
| Validation | **[O]** |
| Compte rendu comme héros de l'écran | **[~]** noyé entre les cartes |

### Plan de traitement (S09) — **[O]** conforme (cartes, statuts français, séquence seulement si énoncée)

### Compte rendu opératoire (S10) — **[O]** conforme (sections seulement si preuve, « à vérifier » séparé)

### Documents — attendu : historique clair et professionnel
**[X]** espace inexistant. Les documents ne vivent que dans leur consultation.

### Paramètres — **[X]** lien mort dans le menu.

### Apprentissage — **[~]** l'écran existe et fonctionne ; présentation brute.

---

## 4. Ce que le benchmark Askara confirme

Leur maturité ne tient pas à leur graphisme, mais à trois décisions produit :

1. **une consultation nourrit plusieurs sorties** (chez eux : MultiDoc ; chez nous :
   l'objet clinique et ses projections — nous avons déjà l'architecture, pas l'interface) ;
2. **le dossier patient se remplit tout seul** : la consultation appartient à un patient
   et à son histoire ;
3. **l'IA est le produit, pas un outil externe** : jamais l'impression de parler à un
   robot à côté du logiciel.

Nous avons les deux premières dans le moteur. Il manque la surface qui les rend visibles.

---

## 5. Architecture cible

```
Oris
├── Accueil            tableau de bord : aujourd'hui · à valider · récent · démarrer
├── Patients           recherche → fiche patient (consultations, documents, plan, historique)
├── Consultations      toutes, groupées par jour, filtrables par état
├── Documents          tous les documents produits, par type et par patient
├── Oris apprend       dictionnaire, préférences, suggestions
└── Paramètres         cabinet, praticien, micro, moteurs, sécurité
```

**Objets et continuité** : `Patient → Consultation → Documents`. Une consultation ne
s'ouvre jamais sans son patient ; un document ne s'ouvre jamais sans sa consultation.
La fiche patient est le point de continuité qui manque aujourd'hui.

**Parcours « wow »**, celui que vous décrivez, en six écrans et deux clics :
`Accueil → patient → écoute → traitement → revue (compte rendu + plan + à vérifier) → validé`.

---

## 6. Système de design à construire

### 6.1 Décision à prendre : la palette
Deux identités existent dans la plaquette.

| | Planche 1 — bleue (figée dans `design/tokens.json`) | Planche 2 — sauge |
|---|---|---|
| Couleurs | `#0F2D46` `#3B82F6` `#7DD3C7` `#EAF1F6` | `#2F6F67` `#CFE5DE` `#EAD9CE` `#F7F6F2` `#2E3A3F` |
| Impression | logiciel clinique, précis, technique | soin, calme, haut de gamme |
| Coût | nul, c'est l'actuel | refonte des jetons, 1 journée |

### 6.2 Fondations
- **Typographie** : Inter **réellement chargée**, échelle 12/14/16/20/24/32/40, chiffres
  tabulaires pour les durées, dents et dates.
- **Espacement** : 4 · 8 · 12 · 16 · 24 · 32 · 48 (déjà spécifié, à appliquer strictement).
- **Rayons** : carte 16, bouton 14.
- **Élévation** : deux niveaux seulement (carte posée, panneau flottant).
- **Mouvement** : une seule pulsation, celle de l'écoute. Rien d'autre ne bouge.

### 6.3 Composants à écrire (aucun n'existe aujourd'hui)
`Button` · `Card` · `PageHeader` · `Chip/Badge` · `Tabs` · `DataTable` · `EmptyState` ·
`SkeletonRow` · `Toast` · `Drawer` · `Dialog` · `SearchField` · `StatusDot` ·
`Timer` · `WaveBar` · `PatientCard` · `EncounterRow` · `DocumentCard` · `FactRow` ·
`EvidencePanel` · `ProcessingSteps`.

### 6.4 Règles non négociables (reprises de la spec)
- l'action principale se comprend en moins de deux secondes ;
- aucun état clinique porté par la couleur seule ;
- aucune métrique inventée sur le tableau de bord ;
- aucun pourcentage de progression qui ne corresponde pas à une étape réelle ;
- jamais de code technique visible par le praticien ;
- chaque écran a ses quatre états : chargement, vide, erreur, hors connexion.

---

## 7. Plan de construction

| Lot | Contenu | Résultat visible |
|---|---|---|
| **L0** | Fondations : police chargée, jetons, 20 composants, page de démonstration interne | Rien ne change pour vous, tout change ensuite |
| **L1** | Coque + Accueil | Un vrai tableau de bord : aujourd'hui, à valider, récent |
| **L2** | Patients + fiche patient | La continuité : consultations, documents, plan, historique |
| **L3** | Nouvelle consultation → écoute → **traitement** | Le parcours, avec l'écran de traitement qui manque |
| **L4** | Revue : compte rendu héros, rail à onglets, faits en français, correction vocale accessible | Le cœur du produit |
| **L5** | Documents | L'historique professionnel |
| **L6** | Apprentissage + Paramètres | Le produit complet |
| **L7** | Finition : états vides, erreurs, clavier, focus, responsive, mouvement | Le niveau commercial |

**Définition du « fini » pour chaque écran** : quatre états traités, navigation au
clavier, focus visible, textes français relus, aucune donnée inventée, aucun code
technique affiché, et une capture d'écran que vous accepteriez de montrer à un confrère.

---

## 8. Décisions qu'il me faut

1. **Palette** : bleue (figée) ou sauge ? Ou les deux à comparer sur un même écran ?
2. **Votre nom et celui du cabinet**, pour que l'accueil dise « Bonjour Docteur Moyal »
   et que les documents portent votre en-tête.
3. **iPhone** : maintenant ou après le site ?
4. **Le mot « patient »** : en V1, un patient est-il créé dans Oris, ou repris d'un
   logiciel existant ? Cela change la fiche patient.
