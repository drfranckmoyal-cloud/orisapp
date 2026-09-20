# Brancher « Votre journée » sur Doctolib

*Note de reprise, écrite le 21 septembre 2026 depuis le projet Dental Lens.
Dire « on branche la journée Doctolib » suffit à reprendre ce chantier.*

---

## Ce qui est déjà fait, ailleurs

Dental Lens (`~/Desktop/Claude-Projects/SMILECLOUD-PHOTOS`, dépôt `smilecloud-photos`)
lit l'agenda Doctolib depuis septembre 2026, en conditions réelles. Son extension Chrome
lit la vue « Liste » d'une journée dans la session ouverte de Franck, **sans API éditeur**,
et livre le résultat à qui le demande.

**Oris n'a donc rien à lire lui-même : il reçoit.**

L'extension livre la journée à chaque destinataire déclaré dans les réglages de Dental
Lens. Oris se déclare avec `http://127.0.0.1:8000/api/journee`. Seules les adresses
locales sont acceptées ; un jeton facultatif part en en-tête `Authorization: Bearer …`.

### Ce que reçoit Oris

```json
{
  "jour": "2026-09-22",
  "rendezvous": [
    {
      "heure": "09:30",
      "patient": "Justine DROIT",
      "prenom": "Justine",
      "nom": "DROIT",
      "motif": "Contrôle périodique",
      "statut": "À venir",
      "dossier_cemedis": ""
    }
  ],
  "diagnostic": { "lignes": 13, "retenus": 11, "ignorees": 2, "agendas": ["…"] }
}
```

`prenom` et `nom` sont déjà séparés (Doctolib écrit « M. DROIT Justine »). Le
`diagnostic` dit ce que l'extension a vu à l'écran : une liste vide s'explique au lieu de
rester muette.

---

## Ce qu'il y a à construire dans Oris

### 1. Recevoir — `POST /api/journee`

Accepte la livraison, garde la journée (un enregistrement par date). Refuser ce qui ne
vient pas de la machine. Rejouer une livraison pour la même date remplace la précédente,
sauf si la nouvelle est vide alors que l'ancienne ne l'était pas (le diagnostic dit si le
tableau a été compris : `diagnostic.entetes === false` = ne pas écraser).

### 2. Rapprocher — sans créer de doublon

**Choix de Franck (21/09/2026) : le rapprochement se fait par le nom**, avec un
pourcentage de ressemblance. Le numéro CEMEDIS existe dans Doctolib mais n'est presque
jamais rempli ; on le range dans l'`identifiant_externe` quand il est là, sans compter
dessus.

Le code est écrit et éprouvé dans `attribution.py` de Dental Lens — **Oris étant en
Python, il se copie presque tel quel** :

- `ressemblance(a, b)` : mots remis en ordre, comparaison lettre à lettre, plus une
  comparaison des noms collés (« DA SILVA » = « DASILVA »). Renvoie 0 à 1.
- Seuils : `SUR = 0.995` (identique → rapproché tout seul), `DOUTE = 0.72`.
- **Règle de sécurité** : Oris ne tranche seul que sur des noms identiques. « Paul » et
  « Paule » se ressemblent à 95 % et sont deux personnes ; attacher une consultation au
  mauvais patient serait pire qu'un doublon.

Quatre états par rendez-vous : `trouve`, `a_confirmer` (avec les candidats et leur
pourcentage), `ambigu` (plusieurs fiches au même nom), `absent`.

### 3. L'écran `/journee`

Remplacer la page « chantier à venir » par :

- la liste du jour, une ligne par rendez-vous : heure, patient, motif ;
- à droite de chaque ligne, **une seule action à la fois** — « ✓ fiche existante »,
  « Créer la fiche », « Vérifier · 90 % » (ouvre les candidats), ou « Commencer la
  consultation » qui crée la fiche au passage ;
- en haut, **« Créer les fiches manquantes »**, actif seulement s'il y a des absents
  confirmés ;
- une journée qui ne contient que des réunions s'affiche comme telle, pas comme une
  liste vide.

L'écran « Préparer la journée » de Dental Lens fait exactement cela : sa mise en page
(semaine navigable à gauche, patients à droite, seule l'action utile est un bouton) est
la référence. Voir `interface/journee.html` du dépôt `smilecloud-photos`.

### 4. Ce qu'il ne faut pas oublier

- **Aucune fiche créée sans certitude.** Tant qu'un nom est « à vérifier », le bouton de
  création n'existe pas, et l'API doit refuser la demande.
- **Une réponse de Franck se retient** : « c'est le même patient » ou « aucun de ceux-là »
  ne doit plus jamais être redemandé.
- Le **cadre juridique** a été tranché le 21/09/2026 : tant qu'Oris tourne sur le Mac du
  cabinet, il relève du même régime que Dental Lens. **À re-trancher avant la première
  mise en ligne.**

---

## Pour essayer sans Doctolib

Une livraison se rejoue à la main :

```bash
curl -s -X POST http://127.0.0.1:8000/api/journee \
  -H 'Content-Type: application/json' \
  -d '{"jour":"2026-09-22","rendezvous":[
        {"heure":"09:30","patient":"Justine ESSAI","prenom":"Justine","nom":"ESSAI",
         "motif":"Contrôle","statut":"À venir","dossier_cemedis":""}]}'
```

Et côté Dental Lens, `POST /api/journee` accepte la même chose : les deux applications
parlent la même langue, ce qui est le début du socle commun.
