# ORIS — MASTER PRODUCT & TECHNICAL SPECIFICATION
## V1 Consultation dentaire, plan de traitement et comptes rendus opératoires ciblés

**Statut :** source de vérité pour Claude Code  
**Version :** 1.2  
**Date :** 16 septembre 2026  
**Langue produit V1 :** français  
**Plateformes V1 :** application iPhone native + application web desktop  
**Nom produit :** Oris

---

# 0. INSTRUCTIONS À CLAUDE CODE

Ce fichier est la source de vérité produit et technique d’Oris V1.

Avant de coder :
1. Lire le document en entier.
2. Ne pas élargir le périmètre fonctionnel sans décision explicite.
3. Construire un produit étroit mais très fini plutôt qu’un logiciel dentaire généraliste.
4. Maintenir une architecture commune entre iPhone et web : même backend, mêmes schémas cliniques, mêmes règles IA.
5. Toute donnée clinique générée doit être traçable vers une source utilisateur ou audio.
6. Ne jamais introduire de donnée clinique « plausible » pour compléter un compte rendu.
7. Toute correction d’un fait clinique doit mettre à jour l’objet clinique central puis les documents dérivés.
8. Ne jamais inscrire de données de santé dans les logs applicatifs ou d’observabilité.
9. Pour le développement local, utiliser uniquement des patients fictifs et des consultations synthétiques.
10. Prévoir l’abstraction STT/LLM dès le premier commit. Aucun fournisseur IA ne doit être codé en dur dans la logique métier.
11. Le code livré à chaque étape doit compiler, être testable et documenté.
12. Maintenir `/docs/DECISIONS.md`, `/docs/KNOWN_LIMITATIONS.md` et `/docs/CHANGELOG.md`.
13. Ne pas implémenter les fonctionnalités explicitement classées « hors périmètre V1 ».
14. Les écrans doivent rester sobres, rapides, tactiles et utilisables pendant une vraie consultation.
15. Toute fonctionnalité clinique doit avoir des tests de non-régression incluant négation, temporalité, incertitude et numéro de dent.

---

# 1. VISION

Oris est un assistant de documentation clinique dentaire.

Il écoute une consultation en direct, identifie les informations médicales réellement exprimées, les transforme en faits cliniques structurés, puis produit :

- un compte rendu de consultation ;
- un plan de traitement structuré ;
- lorsque pertinent, un compte rendu opératoire.

Oris ne doit pas fonctionner comme un simple « audio → résumé ».

Le pipeline fondamental est :

**AUDIO → TRANSCRIPTION → FAITS CLINIQUES → VALIDATION LOGIQUE → OBJET CLINIQUE → DOCUMENTS → VALIDATION PRATICIEN**

Le chirurgien-dentiste reste l’auteur et le validateur clinique final.

---

# 2. PROMESSE PRODUIT

Objectif d’usage :

1. sélectionner ou créer le patient ;
2. démarrer Oris ;
3. conduire normalement la consultation ;
4. terminer l’écoute ;
5. recevoir le compte rendu et le plan de traitement ;
6. vérifier rapidement les points signalés ;
7. corriger si nécessaire, y compris par la voix ;
8. valider ;
9. copier/exporter.

Le praticien ne doit pas avoir à remplir un formulaire pendant la consultation.

Objectif UX : **la consultation produit elle-même le dossier.**

---

# 3. PÉRIMÈTRE V1 — NON NÉGOCIABLE

## 3.1 Inclus

### A. Consultation active
Écoute de la conversation praticien/patient en temps réel.

### B. Compte rendu de consultation
Synthèse clinique structurée et fidèle.

### C. Plan de traitement
Représentation claire des problèmes, options discutées, actes proposés, actes acceptés/refusés/différés et séquence lorsqu’elle a réellement été définie.

### D. Comptes rendus opératoires ciblés
V1 optimisée pour :
- restaurations directes en composite ;
- traitements esthétiques directs ;
- facettes : préparation/provisoires ;
- facettes : collage/cimentation ;
- gestion restauratrice des usures dentaires ;
- restaurations additives liées aux usures ;
- chirurgie orale mineure avec premier template spécialisé « extraction simple/chirurgicale » ;
- template chirurgical générique configurable pour les autres gestes simples.

### E. Corrections
Correction clavier et correction vocale post-consultation.

### F. Export
- copier le texte ;
- PDF ;
- impression ;
- téléchargement du document ;
- préparation d’un export futur vers logiciel métier.

### G. Traçabilité
Lien entre les faits générés et les segments de transcription source.

---

# 4. HORS PÉRIMÈTRE V1

Ne pas développer en V1 :

- implantologie ;
- passeport implantaire ;
- endodontie spécialisée ;
- orthodontie ;
- agenda ;
- facturation ;
- télétransmission ;
- devis financiers ;
- cotation CCAM automatique ;
- gestion comptable ;
- gestion de stock ;
- prescription médicamenteuse autonome ;
- diagnostic autonome ;
- recommandation thérapeutique autonome ;
- interprétation radiologique par IA ;
- analyse automatique de photographies cliniques ;
- messagerie patient ;
- portail patient ;
- application patient ;
- laboratoire/prothésiste ;
- intégrations profondes avec Julie/Logos/Visiodent/etc. ;
- Android natif ;
- dictée médicale généraliste multi-spécialités ;
- entraînement des modèles sur les données utilisateur.

L’architecture doit toutefois permettre d’étendre ultérieurement Oris.

---

# 5. PLATEFORMES

## 5.1 iPhone

Application native Swift / SwiftUI.

Responsabilités :
- authentification ;
- sélection patient ;
- gestion microphone ;
- écoute active ;
- pause/reprise ;
- buffer audio local temporaire ;
- envoi audio sécurisé vers backend ;
- affichage état de session ;
- révision et validation ;
- correction vocale ;
- lecture/export des documents.

L’audio iOS doit utiliser les APIs audio natives adaptées à la capture continue et au streaming.

## 5.2 Web desktop

Application web desktop-first.

Cibles :
- Safari ;
- Chrome ;
- Edge ;
- versions modernes supportées.

Stack recommandée :
- Next.js ;
- React ;
- TypeScript.

La capture micro doit fonctionner exclusivement en HTTPS en production.

## 5.3 Backend commun

iPhone et web consomment la même API et les mêmes schémas métier.

---

# 6. PRINCIPES UX

1. Aucun dashboard inutilement dense.
2. Le bouton principal est toujours identifiable.
3. Pendant la consultation, l’écran doit être lisible à distance.
4. Pas d’obligation de lire la transcription en temps réel.
5. Pas de formulaire clinique à remplir pendant que le patient parle.
6. La validation finale doit être rapide.
7. Les informations incertaines doivent être signalées, pas masquées.
8. Une correction doit demander le moins de manipulations possible.
9. Les formulations IA ne doivent jamais donner une impression de certitude supérieure à la source.
10. Le praticien doit comprendre à tout moment si Oris écoute, est en pause ou a perdu la connexion.

---

# 7. DESIGN PRODUIT

Direction :
- clinique ;
- premium ;
- calme ;
- minimaliste ;
- contemporaine ;
- sans esthétique « chatbot ».

Palette V1 :
- fond clair ;
- texte graphite ;
- une couleur d’accent Oris définie ultérieurement ;
- rouge uniquement pour erreur/arrêt ;
- orange uniquement pour vérification ;
- vert uniquement pour état validé/sûr.

Typographie :
- système natif sur iOS ;
- typographie web sobre et hautement lisible.

Pas de mascotte.
Pas de bulles conversationnelles omniprésentes.
Pas d’animations décoratives pendant une consultation.

---

# 8. ÉCRAN D’ACCUEIL

Contenu minimal :

- logo / Oris ;
- praticien ;
- bouton principal : **Nouvelle consultation** ;
- consultations du jour ;
- documents à valider ;
- recherche patient.

Exemple :

```
Oris

Bonjour Dr X

[ + Nouvelle consultation ]

À valider
• Marie Martin — 14:20
• Jean Dupont — 13:40

Aujourd’hui
✓ Paul Durand — 12:15
✓ Léa Simon — 11:30
```

---

# 9. CRÉATION / SÉLECTION PATIENT

V1 ne doit pas devenir un dossier patient complet.

Champs minimum :
- id interne ;
- prénom ;
- nom ;
- date de naissance facultative au prototype ;
- identifiant externe facultatif ;
- note administrative courte facultative.

Production :
les données patient sont des données de santé/personnelles et doivent être hébergées conformément au cadre retenu.

---

# 10. PRÉ-ÉCRAN CONSULTATION

Affiche :

- patient ;
- praticien ;
- état microphone ;
- information patient : statut à confirmer selon cadrage juridique final ;
- bouton **Commencer l’écoute**.

Maximum : 1 écran avant l’écoute.

---

# 11. ÉCRAN ÉCOUTE ACTIVE

Éléments :

- nom du patient ;
- chronomètre ;
- indicateur microphone ;
- statut réseau ;
- statut de capture ;
- bouton Pause ;
- bouton Terminer ;
- bouton discret « Marquer un point » facultatif ;
- panneau transcript optionnel replié par défaut.

États :

- prêt ;
- écoute ;
- pause ;
- reconnexion ;
- erreur microphone ;
- finalisation.

Aucun élément clinique complexe ne doit distraire le praticien.

---

# 12. DURÉE DE SESSION

V1 :
- objectif nominal : 5 à 60 minutes ;
- durée maximale initiale : 90 minutes.

Une alerte non bloquante peut apparaître avant la limite.

---

# 13. AUDIO — PRINCIPES

## 13.1 Capture

Le flux doit être optimisé pour la parole.

Recommandation :
- mono ;
- codec et fréquence adaptés au fournisseur STT ;
- streaming en chunks ;
- horodatage de chaque chunk ;
- numéro de séquence ;
- mécanisme de reprise après perte réseau.

## 13.2 Résilience

iPhone :
- conserver temporairement le flux/chunks localement pendant la session ;
- réessayer automatiquement l’envoi ;
- supprimer la copie locale après confirmation serveur et finalisation.

Web :
- chunks temporairement conservés côté client pendant la session pour permettre la reprise ;
- suppression dès que le serveur confirme le traitement.

## 13.3 Conservation

Principe V1 production :
- audio éphémère ;
- pas d’archivage permanent par défaut ;
- suppression après transcription/finalisation selon politique technique et juridique validée ;
- toute rétention de debug doit être désactivée par défaut en production.

La transcription et les faits structurés peuvent être conservés dans le dossier Oris selon la politique de rétention retenue.

---

# 14. TRANSCRIPTION

## 14.1 Deux niveaux

### Streaming
Transcription progressive pendant la consultation.

But :
- vérification technique ;
- préparation des faits ;
- latence finale réduite.

### Finalisation
Après arrêt :
- consolidation des segments ;
- correction de ponctuation ;
- diarisation finale si disponible ;
- normalisation des termes dentaires ;
- reconstruction des corrections explicites du discours.

Le document clinique final ne doit pas être fondé uniquement sur la transcription intermédiaire streaming.

---

# 15. DIARISATION ET RÔLES

Rôles possibles :
- praticien ;
- patient ;
- assistant(e) ;
- accompagnant ;
- inconnu.

Le rôle doit avoir un niveau de confiance.

Une information rapportée par le patient n’est pas équivalente à une constatation du praticien.

Exemple :

Patient :
« Je crois que c’est la 26 qui me fait mal. »

Ne doit pas devenir :
« Diagnostic localisé sur 26 ».

Il devient :
« Le patient localise ses symptômes au secteur de la 26 » si la phrase est suffisamment explicite.

---

# 16. NORMALISATION DENTAIRE

## 16.1 Numérotation

Support FDI permanente :
11–18, 21–28, 31–38, 41–48.

Architecture compatible denture temporaire.

Le système doit reconnaître :
- « vingt-six » → 26 ;
- « deux six » si contexte dentaire ;
- « première molaire maxillaire gauche » → 26 si le contexte est suffisamment fiable.

Une normalisation incertaine doit déclencher une vérification.

## 16.2 Surfaces

Valeurs normalisées :
- M : mésial ;
- D : distal ;
- O : occlusal ;
- V/B : vestibulaire/buccal ;
- L : lingual ;
- P : palatin ;
- I : incisal ;
- C : cervical.

Ne pas inventer une surface non exprimée.

---

# 17. OBJET CLINIQUE CENTRAL

Le cœur d’Oris n’est pas le compte rendu mais un **Clinical Encounter Object**.

Toutes les sorties sont générées à partir de cet objet.

Structure conceptuelle :

```json
{
  "encounter_id": "uuid",
  "patient_id": "uuid",
  "practitioner_id": "uuid",
  "started_at": "timestamp",
  "ended_at": "timestamp",
  "status": "review",
  "facts": [],
  "treatment_plan": {},
  "procedures": [],
  "documents": [],
  "warnings": []
}
```

---

# 18. MODÈLE D’UN FAIT CLINIQUE

Chaque fait doit être atomique et traçable.

```json
{
  "fact_id": "uuid",
  "category": "clinical_finding",
  "concept": "cold_test",
  "value": "prolonged_positive_response",
  "teeth": ["26"],
  "surfaces": [],
  "assertion": "present",
  "temporality": "current",
  "clinical_status": "observed",
  "speaker_role": "practitioner",
  "certainty": "certain",
  "source_type": "audio",
  "evidence_segment_ids": ["seg_123"],
  "confidence": 0.93,
  "manually_validated": false
}
```

---

# 19. AXES SÉMANTIQUES OBLIGATOIRES

Chaque information clinique doit pouvoir porter les dimensions suivantes.

## 19.1 Assertion
- present ;
- absent ;
- uncertain.

## 19.2 Temporalité
- past ;
- current ;
- future.

## 19.3 Statut clinique
- patient_reported ;
- observed ;
- clinician_assessment ;
- differential ;
- proposed ;
- accepted ;
- refused ;
- deferred ;
- planned ;
- performed.

## 19.4 Certitude
- certain ;
- probable ;
- possible ;
- unknown.

## 19.5 Provenance
- audio ;
- manual ;
- prior_record.

V1 peut ne pas utiliser `prior_record` tant que le longitudinal n’est pas activé, mais le schéma doit le prévoir.

---

# 20. RÈGLE DE FIDÉLITÉ

Oris ne complète jamais une donnée clinique absente.

Interdit :

Audio :
« On a fait le composite aujourd’hui. »

Sortie inventée :
« Isolation sous digue, mordançage 30 secondes, adhésif universel et composite A2. »

Sortie autorisée :
« Restauration composite réalisée aujourd’hui. »

---

# 21. NÉGATION

La négation est critique.

Audio :
« Pas de douleur nocturne. »

Résultat :
- nocturnal_pain = absent.

Audio :
« Il ne prend plus Eliquis. »

Résultat :
- Eliquis = traitement passé / non actuel.

Audio :
« Je ne pense pas que ce soit une fracture. »

Résultat :
- fracture ne doit pas devenir diagnostic positif.

Tests unitaires obligatoires pour ce domaine.

---

# 22. INCERTITUDE

Audio :
« Il y a peut-être une fissure. »

Résultat :
- concept : crack ;
- assertion : uncertain ;
- certainty : possible.

Document :
« Une fissure est suspectée. »

Interdit :
« Présence d’une fissure. »

---

# 23. TEMPORALITÉ

Audio :
« J’avais proposé des facettes mais aujourd’hui on part plutôt sur des composites. »

Résultat :
- facettes : proposition antérieure/non retenue dans la décision actuelle ;
- composites : proposition/décision actuelle selon le reste du discours.

Oris doit conserver l’historique logique mais ne pas présenter la première option comme plan final.

---

# 24. CORRECTIONS ET CHANGEMENT D’AVIS

Audio :
« La 26… pardon, la 27. »

Résultat final :
- 27.

Audio :
« On va extraire… finalement non, on va surveiller. »

Résultat :
- extraction : proposition annulée/non retenue ;
- surveillance : décision actuelle.

Le moteur doit reconnaître les corrections explicites et la séquence chronologique.

---

# 25. PIPELINE IA

## Étape 1 — Speech-to-text
Produit des segments avec :
- texte ;
- timestamps ;
- confiance ;
- speaker si disponible.

## Étape 2 — Normalisation
- nombres dentaires ;
- termes dentaires ;
- abréviations ;
- marques si dictionnaire utilisateur ;
- corrections phonétiques évidentes avec prudence.

## Étape 3 — Extraction structurée
Le LLM reçoit la transcription finalisée par segments et produit des faits strictement conformes au schéma JSON.

## Étape 4 — Résolution logique
Moteur hybride :
- règles déterministes ;
- modèle IA.

Contrôle :
- négation ;
- temporalité ;
- corrections ;
- contradictions ;
- proposé vs réalisé ;
- patient vs praticien ;
- dent valide.

## Étape 5 — Clinical Encounter Object
Constitution de la source de vérité.

## Étape 6 — Documents
Les documents sont générés depuis l’objet structuré, pas directement depuis l’audio.

## Étape 7 — Validation factuelle
Chaque phrase clinique doit être associable à au moins un fait.

## Étape 8 — Alertes
Les éléments incertains ou contradictoires sont remontés au praticien.

---

# 26. ABSTRACTION DES FOURNISSEURS IA

Créer des interfaces.

```text
SpeechToTextProvider
ClinicalExtractionProvider
DocumentGenerationProvider
ClinicalValidationProvider
```

Aucune logique métier ne doit dépendre d’un fournisseur particulier.

Modes :
- MockProvider pour tests/dev ;
- Provider production configurable par environnement.

Contraintes production :
- traitement de données de santé compatible avec le cadre légal retenu ;
- accord de traitement des données ;
- région appropriée ;
- absence d’usage des données client pour entraînement ;
- politique de rétention contrôlée.

---

# 27. PROMPT SYSTÈME — EXTRACTION CLINIQUE

Implémenter le principe suivant :

> Tu es un moteur d’extraction clinique dentaire. Tu ne rédiges pas un compte rendu. Tu convertis uniquement les informations explicitement présentes dans les segments fournis en faits atomiques conformes au schéma. Tu ne complètes jamais une information manquante. Tu préserves la négation, la temporalité, l’incertitude, le rôle du locuteur et la distinction entre proposition, acceptation, refus, planification et acte réellement réalisé. En cas de doute, tu marques l’information comme incertaine ou tu l’omets. Une connaissance médicale générale ne constitue jamais une source suffisante pour créer un fait.

Sortie :
JSON strict validé par schéma.

---

# 28. PROMPT SYSTÈME — GÉNÉRATION DOCUMENTAIRE

Principe :

> Tu rédiges uniquement à partir du Clinical Encounter Object fourni. Aucun fait clinique absent de cet objet ne peut apparaître. Tu peux reformuler pour améliorer la lisibilité mais tu ne dois pas augmenter le degré de certitude. Tu distingues les faits rapportés par le patient, les observations, les hypothèses, les options discutées, le traitement retenu et les actes réalisés. Les sections sans contenu utile sont omises.

---

# 29. VALIDATEUR ANTI-HALLUCINATION

Après génération :

1. découper le document en propositions ;
2. vérifier pour chaque proposition la présence de faits support ;
3. comparer :
   - dents ;
   - nombres ;
   - diagnostics ;
   - médicaments ;
   - matériaux ;
   - actes ;
   - temporalité ;
   - statut proposé/accepté/réalisé ;
4. signaler toute phrase non supportée ;
5. régénérer ou demander vérification.

Aucun document ne peut passer automatiquement à `validated`.

---

# 30. PROVENANCE / « POURQUOI ORIS A ÉCRIT ÇA ? »

Dans l’écran de révision, une phrase ou un fait doit pouvoir afficher sa source.

Exemple :

Compte rendu :
« Le patient rapporte des sensibilités au froid sur 11 et 21. »

Action :
tap/clic → panneau source :

> Patient — 14:32:10  
> « J’ai surtout froid sur les deux dents devant… »

Cette fonction est prioritaire en V1.

---

# 31. SCORE DE CONFIANCE

Le score interne ne doit pas être présenté comme une probabilité médicale.

Il sert à l’interface.

Catégories UI :
- fiable ;
- à vérifier ;
- conflit.

Déclencheurs :
- faible confiance STT ;
- dent ambiguë ;
- correction contradictoire ;
- interlocuteur incertain ;
- concept non reconnu ;
- donnée opératoire importante absente.

---

# 32. COMPTE RENDU DE CONSULTATION

## 32.1 Sections possibles

Les sections sont affichées uniquement si elles contiennent des données.

Ordre recommandé :
1. Motif de consultation
2. Éléments anamnestiques pertinents
3. Symptômes rapportés
4. Examen clinique
5. Examens complémentaires discutés/consultés
6. Analyse / diagnostic / hypothèses
7. Options thérapeutiques discutées
8. Décision / plan retenu
9. Informations et limites expliquées
10. Suite / contrôle

## 32.2 Style

Par défaut :
- médical ;
- synthétique ;
- phrases complètes ;
- pas de répétition ;
- pas de jargon inutile ;
- suffisamment détaillé pour le dossier.

Préférences praticien :
- court ;
- standard ;
- détaillé.

---

# 33. PLAN DE TRAITEMENT — OBJET STRUCTURÉ

Le plan de traitement est un objet distinct mais dérivé du même Encounter.

```json
{
  "goals": [],
  "items": [
    {
      "item_id": "uuid",
      "teeth": ["11", "21"],
      "problem": "usure incisive",
      "action": "restauration additive en composite",
      "status": "proposed",
      "priority": "routine",
      "sequence": null,
      "alternatives": [],
      "prerequisites": [],
      "uncertainties": [],
      "evidence_fact_ids": []
    }
  ],
  "notes": []
}
```

## 33.1 Status autorisés
- discussed ;
- proposed ;
- accepted ;
- refused ;
- deferred ;
- planned ;
- completed.

## 33.2 Règle
Oris ne choisit jamais une option thérapeutique à la place du praticien.

Si plusieurs options ont été discutées sans décision :
elles doivent toutes rester « discussed/proposed ».

## 33.3 Séquençage
Ne pas inventer des phases.

Si le praticien dit :
« On commence par blanchiment, puis composites 11/21, puis contrôle. »

Alors Oris crée la séquence 1/2/3.

Sinon :
`sequence = null`.

---

# 34. ÉCRAN PLAN DE TRAITEMENT

Présentation par cartes.

Exemple :

```
PLAN DE TRAITEMENT

1  Blanchiment
   Statut : accepté

2  11 / 21 — restaurations additives en composite
   Statut : proposé

3  Contrôle
   Statut : prévu

[ Modifier ] [ Valider ]
```

Le praticien peut :
- réordonner ;
- corriger ;
- changer le statut ;
- ajouter manuellement ;
- supprimer.

Toute modification doit mettre à jour l’objet clinique.

---

# 35. CONSULTATION ESTHÉTIQUE — ONTOLOGIE V1

Oris doit savoir extraire lorsque ces informations sont réellement exprimées :

## Demande
- couleur ;
- forme ;
- longueur ;
- alignement ;
- espaces/diastèmes ;
- anciennes restaurations ;
- usures ;
- asymétrie ;
- sourire ;
- attente patient.

## Analyse décrite par le praticien
- teinte ;
- proportions ;
- axes ;
- bords incisifs ;
- exposition dentaire ;
- ligne du sourire ;
- architecture gingivale ;
- position dentaire ;
- usure ;
- support d’émail ;
- restaurations existantes ;
- occlusion ;
- parafonction ;
- sensibilité ;
- contexte parodontal lorsqu’il est évoqué.

## Moyens diagnostiques mentionnés
- photographies ;
- scan ;
- empreinte ;
- mock-up ;
- wax-up ;
- radiographie.

Oris ne doit PAS analyser lui-même ces images en V1.

## Options possibles si réellement discutées
- blanchiment ;
- composite direct ;
- fermeture de diastème ;
- facettes directes ;
- facettes céramiques ;
- orthodontie ;
- couronne/onlay/overlay si cité ;
- surveillance ;
- combinaison de traitements.

---

# 36. USURES DENTAIRES — ONTOLOGIE V1

Extraire lorsque dit :

## Présentation
- usure généralisée/localisée ;
- secteur ;
- perte de longueur ;
- facettes d’usure ;
- exposition dentinaire ;
- hypersensibilité ;
- fracture/écaillage associé.

## Facteurs évoqués
- alimentation acide ;
- reflux ;
- vomissements ;
- bruxisme ;
- parafonction ;
- habitudes ;
- brossage ;
- médicaments/sécheresse si discutés.

Aucune étiologie ne doit être inventée.

## Évaluation
- occlusion ;
- espace restaurateur ;
- DVO si explicitement discutée ;
- photographies ;
- scan ;
- suivi comparatif.

## Solutions discutées
- prévention ;
- surveillance ;
- composite additif ;
- wax-up/mock-up ;
- restaurations indirectes ;
- prise en charge étiologique ;
- gouttière si évoquée.

Les scores type BEWE ne sont jamais calculés automatiquement sans données dédiées et validation métier ultérieure.

---

# 37. COMPTE RENDU OPÉRATOIRE — PRINCIPES

Un compte rendu opératoire doit distinguer :

- indication ;
- site/dents ;
- acte réellement réalisé ;
- anesthésie si exprimée ;
- isolation si exprimée ;
- préparation ;
- étapes techniques réellement évoquées ;
- matériaux réellement cités ;
- contrôle ;
- finition ;
- complications ;
- recommandations ;
- suite.

Aucune étape standard ne doit apparaître uniquement parce qu’elle est « normalement » réalisée.

---

# 38. TEMPLATE — RESTAURATION COMPOSITE

Champs structurés possibles :

- dent(s) ;
- surfaces ;
- indication ;
- diagnostic/constat ;
- anesthésie ;
- isolation ;
- ancienne restauration déposée ;
- préparation ;
- protection pulpaire si dite ;
- protocole adhésif ;
- adhésif/marque ;
- composite/marque ;
- teinte ;
- technique de stratification ;
- matrice ;
- point de contact ;
- finition ;
- polissage ;
- contrôle occlusal ;
- complication ;
- instruction/suite.

Le document omet les champs non renseignés.

---

# 39. TEMPLATE — TRAITEMENT ESTHÉTIQUE DIRECT

Pour :
- fermeture de diastème ;
- modification de forme ;
- facette composite directe ;
- reconstruction additive antérieure.

Champs :
- demande/indication ;
- dents ;
- plan esthétique validé ;
- mock-up/guide si mentionné ;
- anesthésie ;
- isolation ;
- préparation minimale/absence de préparation si explicitement dit ;
- adhésif ;
- composites/teintes ;
- stratification ;
- morphologie ;
- embrasures/contacts ;
- finition ;
- polissage ;
- occlusion ;
- photographie si mentionnée ;
- contrôle prévu.

---

# 40. TEMPLATE — FACETTES : PRÉPARATION / PROVISOIRES

Champs :
- dents ;
- indication ;
- validation esthétique préalable si mentionnée ;
- mock-up ;
- anesthésie ;
- réduction guidée ;
- design de préparation ;
- limites ;
- conservation d’émail si mentionnée ;
- empreinte/scan ;
- teinte ;
- provisoires ;
- technique provisoire ;
- recommandations ;
- prochain rendez-vous.

Ne pas inventer de valeurs de réduction.

---

# 41. TEMPLATE — FACETTES : COLLAGE / CIMENTATION

Champs :
- dents ;
- type de restauration ;
- essayage ;
- validation esthétique ;
- teinte du ciment si dite ;
- isolation ;
- traitement de surface céramique réellement dicté ;
- traitement de surface dentaire réellement dicté ;
- adhésif ;
- ciment/composite de collage ;
- photopolymérisation ;
- élimination des excès ;
- finition ;
- contacts ;
- contrôle occlusal ;
- photographie ;
- complications ;
- consignes ;
- contrôle.

Règle majeure :
ne jamais insérer automatiquement « acide fluorhydrique », « silane », « mordançage » ou une durée si cela n’a pas été dicté.

---

# 42. TEMPLATE — USURES : RESTAURATION ADDITIVE

Champs :
- contexte d’usure ;
- dents/secteurs ;
- objectif ;
- protocole préopératoire évoqué ;
- wax-up/mock-up/clé ;
- anesthésie ;
- isolation ;
- support ;
- adhésif ;
- composite ;
- teintes ;
- technique additive ;
- reconstruction anatomique ;
- contrôle fonctionnel/occlusal ;
- finition/polissage ;
- information patient ;
- suivi.

Concepts tels que Dahl, augmentation de DVO ou modification occlusale ne sont inscrits que s’ils sont explicitement présents.

---

# 43. TEMPLATE — EXTRACTION SIMPLE / CHIRURGICALE

Champs :
- dent ;
- indication ;
- anesthésie ;
- type d’extraction ;
- lambeau si mentionné ;
- ostéotomie si mentionnée ;
- odontosection si mentionnée ;
- avulsion ;
- curetage si mentionné ;
- irrigation si mentionnée ;
- contrôle ;
- hémostase ;
- sutures ;
- complication ;
- prescription réellement effectuée ;
- consignes ;
- suivi.

Le système n’ajoute jamais un antibiotique, un antalgique ou une consigne non évoquée.

---

# 44. TEMPLATE — CHIRURGIE MINEURE GÉNÉRIQUE

V1 permet de créer un template personnalisable comprenant :
- indication ;
- site ;
- anesthésie ;
- incision/abord ;
- geste ;
- matériel/biomatériau si dicté ;
- hémostase ;
- sutures ;
- incident/complication ;
- consignes ;
- contrôle.

Ce template sert de transition tant que les gestes chirurgicaux spécifiques n’ont pas été cadrés.

---

# 45. DOCUMENT OPÉRATOIRE — DÉTECTION DES INFORMATIONS MANQUANTES

Pour les templates opératoires, Oris peut afficher :

**À vérifier**
- dent/site ambigu ;
- matériau mentionné mais nom mal reconnu ;
- teinte incertaine ;
- absence de précision sur une donnée que le praticien a configurée comme « importante ».

Important :
une information manquante ne doit jamais être automatiquement remplie.

Le praticien choisit :
- compléter ;
- ignorer.

---

# 46. CORRECTION VOCALE

Écran de révision :
bouton microphone **Corriger par la voix**.

Exemples :
- « Remplace 26 par 27. »
- « La facette concerne aussi la 12. »
- « Retire la phrase sur la sensibilité. »
- « Le patient a finalement accepté les composites. »
- « Fais le compte rendu plus court. »

Deux types de commandes :

## A. Correction clinique
Met à jour le Clinical Encounter Object.

## B. Préférence rédactionnelle
Modifie uniquement la présentation du document.

Le moteur doit distinguer les deux.

---

# 47. PATCH STRUCTURÉ POUR CORRECTION

Une correction clinique ne modifie pas directement le texte.

Pipeline :

1. interpréter la commande ;
2. produire un patch structuré ;
3. montrer une confirmation si impact significatif ;
4. appliquer au Clinical Encounter Object ;
5. invalider les documents dérivés ;
6. régénérer ;
7. garder l’historique de version.

Exemple :

```json
{
  "operation": "replace_tooth_reference",
  "from": "26",
  "to": "27",
  "affected_fact_ids": ["f1", "f2"]
}
```

---

# 48. ÉDITEUR MANUEL

Le praticien peut éditer le texte.

Mais si une modification manuelle change une donnée clinique importante, Oris doit proposer :

« Mettre également à jour les données cliniques de la consultation ? »

Objectif :
éviter qu’un document dise 27 tandis que le plan de traitement reste sur 26.

---

# 49. ÉTATS D’UNE CONSULTATION

State machine :

```text
draft
→ recording
↔ paused
→ finalizing
→ processing
→ review
→ validated
→ exported
→ archived
```

États d’erreur :
- audio_error ;
- upload_interrupted ;
- transcription_failed ;
- generation_failed.

Toutes les erreurs doivent permettre une récupération sans duplication de consultation.

---

# 50. ÉTATS DES DOCUMENTS

- draft_ai ;
- needs_review ;
- validated ;
- exported ;
- superseded.

Une validation est une action explicite du praticien.

---

# 51. ÉCRAN POST-CONSULTATION

Structure :

```
Consultation terminée

Oris prépare le dossier…

[ Compte rendu ]
[ Plan de traitement ]
[ Opératoire ]  ← seulement si pertinent

À vérifier (2)
• dent entendue « 16 ou 26 »
• nom du composite incertain

[ Corriger par la voix ]
[ Valider ]
```

La présence d’un compte rendu opératoire peut être :
- sélectionnée manuellement ;
- proposée par Oris si un acte réalisé est détecté.

Oris ne doit jamais classer un acte comme réalisé sans preuve suffisante.

---

# 52. ÉCRAN DE RÉVISION

Desktop :
- colonne gauche : document ;
- colonne droite : points à vérifier / données structurées ;
- panneau source sur demande.

iPhone :
- document plein écran ;
- onglet « À vérifier » ;
- bottom sheet pour source/correction.

Actions :
- éditer ;
- corriger par la voix ;
- raccourcir/allonger ;
- afficher source ;
- valider ;
- exporter.

---

# 53. PRÉFÉRENCES RÉDACTIONNELLES

V1 :
- longueur : courte / standard / détaillée ;
- style : phrases / semi-télégraphique ;
- choix terminologiques simples ;
- expressions préférées.

Exemples :
- extraction ↔ avulsion ;
- vestibulaire ↔ buccal selon préférences ;
- CR compact vs narratif.

L’apprentissage automatique à partir des corrections peut être préparé mais ne doit pas être autonome en V1.

---

# 54. DICTIONNAIRE PERSONNEL

Le praticien peut ajouter :
- marques de composites ;
- adhésifs ;
- ciments ;
- matériaux ;
- laboratoires ;
- noms de confrères ;
- termes techniques.

Champs :
- terme canonique ;
- variantes phonétiques/écrites ;
- catégorie.

Exemple :
```json
{
  "canonical": "G-ænial A’CHORD",
  "aliases": ["genial accord", "G A chord"],
  "category": "composite"
}
```

---

# 55. PIÈCES JOINTES

V1 peut permettre d’attacher :
- photo ;
- PDF ;
- radiographie ;
- autre document.

Mais :
- aucune interprétation par IA ;
- aucune extraction diagnostique ;
- elles servent uniquement de pièce liée à la consultation.

Peut être reporté après le premier MVP si cela ralentit le cœur audio.

---

# 56. MODÈLE DE DONNÉES — ENTITÉS

Tables/collections conceptuelles :

## users
- id
- email
- name
- role
- preferences
- created_at

## organizations
Prévoir même si V1 bêta mono-praticien.

## organization_members

## patients
- id
- organization_id
- first_name
- last_name
- birth_date nullable
- external_id nullable
- created_at

## encounters
- id
- patient_id
- practitioner_id
- started_at
- ended_at
- status
- mode
- metadata

## audio_sessions
- id
- encounter_id
- provider
- status
- started_at
- ended_at
- purge_status

## transcript_segments
- id
- encounter_id
- start_ms
- end_ms
- speaker_role
- text
- confidence
- is_final

## clinical_facts
- id
- encounter_id
- category
- concept
- value_json
- assertion
- temporality
- clinical_status
- certainty
- confidence
- source_type
- validated

## fact_evidence_links
- fact_id
- transcript_segment_id

## treatment_plans
- id
- encounter_id
- status
- goals_json

## treatment_plan_items
- id
- plan_id
- teeth_json
- problem
- action
- status
- priority
- sequence
- data_json

## procedures
- id
- encounter_id
- procedure_type
- status
- structured_data_json

## documents
- id
- encounter_id
- document_type
- status
- current_version_id

## document_versions
- id
- document_id
- version
- content
- generated_from_object_version
- created_by
- created_at

## templates
- id
- organization_id nullable
- type
- name
- schema_json
- prompt_config_json

## glossary_terms

## attachments

## audit_events

## prompt_versions

## model_runs
Ne jamais y stocker inutilement du contenu patient en clair dans les métadonnées de logs.

---

# 57. VERSIONING DE L’OBJET CLINIQUE

Chaque modification importante incrémente :

`encounter_object_version`

Les documents mémorisent :
`generated_from_object_version`.

Si l’objet passe de V4 à V5 :
les documents issus de V4 deviennent `outdated` jusqu’à régénération.

---

# 58. API — DOMAINES

Prévoir API REST claire.

## Auth
- POST /auth/login
- POST /auth/logout
- POST /auth/mfa/verify

## Patients
- GET /patients
- POST /patients
- GET /patients/:id
- PATCH /patients/:id

## Encounters
- POST /encounters
- GET /encounters/:id
- POST /encounters/:id/start
- POST /encounters/:id/pause
- POST /encounters/:id/resume
- POST /encounters/:id/finish
- POST /encounters/:id/validate

## Audio
- POST /encounters/:id/audio/chunk
ou WebSocket/stream dédié.

## Transcript
- GET /encounters/:id/transcript

## Clinical object
- GET /encounters/:id/clinical-object
- PATCH /encounters/:id/clinical-object

## Corrections
- POST /encounters/:id/corrections/voice
- POST /encounters/:id/corrections/text

## Documents
- GET /encounters/:id/documents
- POST /encounters/:id/documents/generate
- POST /documents/:id/validate
- GET /documents/:id/export?format=pdf|text

## Preferences
- GET/PATCH /me/preferences

## Glossary
- GET/POST/PATCH /glossary

---

# 59. COMMUNICATION TEMPS RÉEL

Préférer WebSocket pour :
- état streaming ;
- segments transcript ;
- progression traitement ;
- erreurs de flux ;
- événements de reconnexion.

Le backend doit traiter les chunks idempotemment.

Chaque chunk :
- session_id ;
- sequence ;
- timestamp ;
- checksum ;
- payload.

---

# 60. ARCHITECTURE BACKEND RECOMMANDÉE

Approche V1 :
**modular monolith**, pas microservices prématurés.

Recommandation :
- FastAPI / Python pour API et orchestration IA ;
- PostgreSQL ;
- Redis pour queue/cache/locks si nécessaire ;
- worker asynchrone pour finalisation STT et génération ;
- stockage objet compatible S3 dans environnement conforme ;
- WebSocket pour temps réel ;
- Docker pour dev et déploiement.

Éviter d’introduire Kubernetes tant que la charge ne le justifie pas.

---

# 61. STRUCTURE DU REPOSITORY

```text
oris/
  apps/
    web/
    ios/
  services/
    api/
    worker/
  packages/
    schemas/
    clinical-ontology/
    prompt-assets/
    test-fixtures/
  infra/
    docker/
    deployment/
  docs/
    MASTER_SPEC.md
    DECISIONS.md
    CHANGELOG.md
    KNOWN_LIMITATIONS.md
    SECURITY.md
    AI_EVALS.md
  scripts/
  README.md
```

Les schémas JSON doivent être partageables entre backend/web et permettre une génération de modèles Swift lorsque pertinent.

---

# 62. AUTHENTIFICATION ET RÔLES

V1 :
- email ;
- mot de passe robuste ;
- MFA obligatoire en production.

Rôles prévus :
- practitioner ;
- assistant ;
- admin.

Bêta initiale :
- priorité practitioner.

Règle :
seul le praticien valide un document clinique final dans la V1.

---

# 63. SÉCURITÉ

Non négociable :

- TLS ;
- chiffrement des données au repos ;
- secrets hors repo ;
- rotation secrets ;
- MFA ;
- moindre privilège ;
- audit log ;
- sauvegardes chiffrées ;
- restauration testée ;
- séparation dev/staging/prod ;
- aucune donnée de santé réelle en dev ;
- pas de contenu clinique dans Sentry/logs par défaut ;
- masquage des identifiants sensibles ;
- contrôle des exports.

---

# 64. HÉBERGEMENT / DONNÉES DE SANTÉ

Oris traite des données de santé.

Production France :
- architecture sur infrastructure adaptée au cadre HDS applicable ;
- validation du périmètre exact de certification avec conseil compétent ;
- cartographie complète des sous-traitants ;
- traitement/résidence/transferts documentés ;
- DPA/accords adaptés ;
- anticiper les évolutions du référentiel HDS ;
- revue juridique/RGPD avant utilisation avec de vraies données patient.

Le développement peut être réalisé localement avec données synthétiques avant choix définitif du fournisseur de production.

---

# 65. AUDIO ET INFORMATION PATIENT

Oris doit techniquement rendre impossible une écoute « cachée » par l’interface.

Toujours afficher :
- état micro ;
- état d’écoute ;
- pause ;
- arrêt.

Le workflow d’information/consentement patient doit être paramétrable afin d’appliquer la procédure juridique validée avant mise en production.

Ne pas figer dans le code une interprétation juridique non validée.

---

# 66. POLITIQUE IA

Production :
- aucune utilisation des données utilisateur pour entraîner un modèle général ;
- aucun prompt de production conservé par un fournisseur au-delà du nécessaire sans validation ;
- configuration de rétention connue ;
- audit des fournisseurs ;
- capacité de remplacer un fournisseur sans réécrire le domaine clinique.

---

# 67. OBSERVABILITÉ

Mesurer :
- durée session ;
- nombre de chunks ;
- latence STT ;
- latence finalisation ;
- latence extraction ;
- latence génération ;
- erreurs techniques ;
- taux de reconnexion ;
- nombre de corrections ;
- document validé sans correction ;
- nombre de warnings.

Ne jamais journaliser :
- nom patient ;
- transcript brut ;
- compte rendu ;
- diagnostic ;
- audio ;
- autre donnée de santé, sauf système d’audit clinique dédié et sécurisé explicitement prévu.

---

# 68. OBJECTIFS DE PERFORMANCE

Cibles produit :

## Démarrage écoute
< 2 secondes après autorisation et action utilisateur dans des conditions normales.

## Feedback streaming
premier signal d’activité immédiat ;
premier texte si affiché : quelques secondes maximum selon fournisseur.

## Finalisation après arrêt
objectif :
- note initiale exploitable < 15 secondes pour une consultation standard lorsque l’infrastructure le permet.

Ce sont des objectifs et non des garanties réglementaires.

## Correction
objectif < 5 secondes.

---

# 69. MODE DÉGRADÉ RÉSEAU

Si connexion perdue :

1. l’interface indique clairement « connexion interrompue » ;
2. la capture locale continue si possible ;
3. les chunks sont mis en attente ;
4. reprise automatique ;
5. aucune partie audio n’est silencieusement abandonnée ;
6. si perte irrécupérable, Oris l’indique avant génération.

Interdit :
générer un compte rendu comme si la consultation avait été entièrement captée lorsqu’une portion est manquante.

---

# 70. GESTION DES INTERRUPTIONS iOS

Tester :
- appel entrant ;
- Siri ;
- changement route audio ;
- AirPods connexion/déconnexion ;
- verrouillage écran ;
- passage bref en arrière-plan ;
- coupure réseau.

Le comportement exact autorisé par iOS doit être respecté.

Toute interruption doit être visible et journalisée techniquement.

---

# 71. PERMISSIONS MICRO

iOS :
- demander explicitement l’autorisation microphone ;
- fournir une description claire de l’usage ;
- gérer refus et réactivation dans Réglages.

Web :
- microphone uniquement dans un contexte sécurisé ;
- gérer refus d’autorisation ;
- permettre de choisir l’entrée audio si utile ultérieurement.

---

# 72. DONNÉES DE TEST SYNTHÉTIQUES

Créer au minimum 50 scénarios synthétiques V1 avant bêta clinique.

Catégories :
- consultation esthétique ;
- usures ;
- composites ;
- facettes ;
- extraction ;
- conversation sans données importantes ;
- accent ;
- bruit ;
- correction de dent ;
- négation ;
- changement de décision ;
- médicament arrêté ;
- hypothèse diagnostique ;
- patient qui emploie un mauvais numéro de dent ;
- praticien qui se corrige ;
- accompagnant qui parle.

Aucune donnée patient réelle.

---

# 73. GOLDEN TESTS

Pour chaque scénario :

Entrée :
transcription annotée.

Attendus :
- faits ;
- dents ;
- temporalité ;
- assertion ;
- statut ;
- plan ;
- document.

Les résultats sont versionnés.

Toute modification de prompt/modèle doit exécuter les golden tests.

---

# 74. TESTS CRITIQUES

## Test A
« La 26… pardon la 27. »
Attendu : 27.

## Test B
« Pas de douleur au froid. »
Attendu : cold_sensitivity = absent.

## Test C
« Peut-être une fissure sur la 16. »
Attendu : fissure possible, pas certaine.

## Test D
« J’avais proposé des facettes, mais on fera des composites. »
Attendu : composites = plan actuel ; facettes = option antérieure/non retenue.

## Test E
« On pourrait faire un blanchiment ou ne rien faire pour le moment. »
Attendu : deux options discutées ; aucune acceptée.

## Test F
« On a fait le composite sur 11 aujourd’hui. »
Attendu : composite 11 = performed.

## Test G
« La prochaine fois on fera le composite sur 11. »
Attendu : planned, pas performed.

## Test H
Patient : « je pense que c’est une carie »
Attendu : patient_reported belief, pas diagnostic praticien.

## Test I
« Je ne prends plus d’Eliquis. »
Attendu : pas traitement actuel.

## Test J
Perte audio de 2 minutes.
Attendu : warning critique ; pas de fausse impression d’exhaustivité.

---

# 75. MÉTRIQUES DE QUALITÉ CLINIQUE

Ne pas piloter uniquement par Word Error Rate.

Mesures clés :

- Tooth Number Accuracy ;
- Clinical Fact Precision ;
- Clinical Fact Recall ;
- Negation Accuracy ;
- Temporality Accuracy ;
- Plan-vs-Performed Accuracy ;
- Speaker Attribution Accuracy ;
- Unsupported Statement Rate ;
- Correction Rate ;
- Validated Without Edit Rate ;
- Critical Error Rate.

Objectif principal :
**zéro affirmation clinique inventée** doit être la direction produit, même si un système probabiliste ne permet pas de promettre mathématiquement zéro erreur.

---

# 76. TYPOLOGIE D’ERREURS

P0 critique :
- mauvaise dent ;
- traitement réalisé au lieu de proposé ;
- diagnostic certain au lieu d’hypothèse ;
- médicament présenté comme actuel alors qu’arrêté ;
- acte inventé ;
- matériau inventé ;
- négation inversée ;
- portion audio manquante non signalée.

P1 :
- mauvais terme technique sans changement de sens ;
- omission secondaire ;
- mauvaise attribution de speaker sans impact clinique.

P2 :
- style ;
- ponctuation ;
- formulation.

Les P0 doivent bloquer la montée en production s’ils dépassent le seuil défini lors des évaluations.

---

# 77. TEMPLATES ET SCHEMAS

Les templates ne doivent pas être des paragraphes préremplis où l’IA complète les trous.

Ils doivent définir :
- catégories attendues ;
- ordre de présentation ;
- importance relative ;
- champs critiques ;
- règles de validation.

La sortie n’affiche que les éléments soutenus par des faits.

---

# 78. EXPORT PDF

PDF :
- logo Oris discret ou logo cabinet configurable ;
- identité praticien ;
- identité patient ;
- date ;
- type de document ;
- contenu ;
- mention validation ;
- pagination ;
- mise en page A4 propre.

Aucune signature numérique qualifiée en V1.

---

# 79. COPIER-COLLER LOGICIEL MÉTIER

V1 :
bouton **Copier pour le dossier**.

Formats :
- texte simple ;
- texte structuré.

Préparer ultérieurement :
- intégrations API ;
- extension navigateur ;
- deep links éventuels.

Ne pas automatiser l’écriture dans les logiciels métiers en V1.

---

# 80. PARCOURS PRINCIPAL — CONSULTATION

```text
Home
→ Patient
→ Nouvelle consultation
→ Vérification micro / information patient
→ Start
→ Écoute
→ Stop
→ Finalisation
→ Compte rendu + plan
→ Warnings
→ Corrections
→ Validation
→ Export
```

Nombre de manipulations pendant la consultation :
idéalement 2 :
- start ;
- stop.

---

# 81. PARCOURS — ACTE EFFECTUÉ PENDANT LA CONSULTATION

Si Oris détecte un acte réalisé :

post-consultation :
« Un acte opératoire a été détecté. Générer le compte rendu opératoire ? »

Choix :
- Oui ;
- Non.

Le type peut être suggéré :
- composite ;
- esthétique direct ;
- facette préparation ;
- facette collage ;
- usures additif ;
- extraction ;
- autre chirurgie.

Le praticien confirme si la détection n’est pas certaine.

---

# 82. PREMIER ONBOARDING

Étapes :
1. compte ;
2. identité praticien ;
3. test microphone ;
4. préférences rédactionnelles ;
5. dictionnaire facultatif ;
6. mini consultation fictive de démonstration.

Ne pas demander 30 paramètres avant de pouvoir tester le produit.

---

# 83. LANGUAGE / I18N

V1 interface :
français.

V1 entrée principale :
français.

Architecture :
i18n-ready.

Ne pas développer le multilingue tant que le cœur français n’est pas excellent.

---

# 84. ACCESSIBILITÉ

- taille dynamique raisonnable ;
- contrastes ;
- boutons ≥ cible tactile recommandée ;
- état microphone non dépendant uniquement d’une couleur ;
- labels VoiceOver sur iOS ;
- navigation clavier web de base.

---

# 85. FEATURE FLAGS

Prévoir :
- live_transcript ;
- operative_generation ;
- voice_correction ;
- attachments ;
- advanced_warnings.

Permet bêta contrôlée sans branches de code parallèles.

---

# 86. ENVIRONNEMENTS

- local ;
- test ;
- staging ;
- production.

Chaque environnement possède :
- DB distincte ;
- clés distinctes ;
- stockage distinct ;
- fournisseurs IA configurables.

Production ne doit jamais réutiliser une clé dev.

---

# 87. MIGRATIONS

Toute évolution DB passe par migration versionnée.

Aucune modification manuelle de prod non reproductible.

---

# 88. SAUVEGARDES

Production :
- sauvegarde DB ;
- chiffrement ;
- rétention documentée ;
- test de restauration ;
- plan de reprise.

Les backups contenant des données de santé doivent suivre le même niveau de protection que la donnée primaire.

---

# 89. AUDIT LOG

Événements :
- login ;
- consultation créée ;
- écoute démarrée/arrêtée ;
- document généré ;
- fait modifié ;
- document validé ;
- export ;
- suppression.

Le journal doit référencer les IDs, pas recopier le contenu clinique.

---

# 90. SUPPRESSION

Prévoir :
- suppression audio automatique ;
- suppression patient/consultation selon règles légales et permissions ;
- traçabilité de suppression ;
- purge des blobs ;
- politique backup documentée.

Les obligations légales de conservation du dossier médical ne doivent pas être codées à partir d’hypothèses : validation juridique avant production.

---

# 91. RECHERCHE

V1 :
- patient ;
- date ;
- type de document.

Pas de recherche sémantique dans les dossiers en V1.

---

# 92. CONTEXTE LONGITUDINAL

Non activé dans la première release.

Préparer le modèle mais ne pas injecter automatiquement l’historique patient dans une nouvelle consultation.

Raison :
éviter que des faits historiques soient présentés comme constatés aujourd’hui.

Future V2 :
contexte explicite avec provenance `prior_record`.

---

# 93. NOTIFICATIONS

V1 :
- document restant à valider ;
- traitement de consultation terminé si finalisation asynchrone.

Pas de notifications marketing.

---

# 94. MODE « RÉDACTION SEULE »

Pas prioritaire V1.

Si implémenté ultérieurement :
courte dictée post-consultation utilisant le même Clinical Encounter Object.

Ne pas retarder l’écoute active pour développer ce mode.

---

# 95. PERSONNALISATION DE TEMPLATE

V1.0 :
templates Oris fixes + quelques préférences.

V1.x :
éditeur de template contrôlé.

Ne pas permettre au praticien de créer des templates capables d’inventer des champs cliniques par défaut.

---

# 96. FRONTEND WEB — RECOMMANDATIONS

- Next.js App Router ;
- TypeScript strict ;
- composants accessibles ;
- gestion état serveur avec solution simple ;
- WebSocket dédié capture/statut ;
- éditeur texte contrôlé ;
- tests Playwright pour flux critiques ;
- aucune donnée clinique dans analytics tiers.

---

# 97. iOS — RECOMMANDATIONS

- SwiftUI ;
- architecture testable ;
- async/await ;
- client API typé ;
- Keychain pour tokens ;
- stockage temporaire audio sécurisé ;
- gestion interruption audio ;
- gestion route audio ;
- tests unitaires du state machine ;
- UI tests du parcours start/stop/review.

---

# 98. BACKEND — RECOMMANDATIONS

Python :
- FastAPI ;
- Pydantic ;
- SQLAlchemy/SQLModel selon choix, mais un seul ORM cohérent ;
- Alembic migrations ;
- PostgreSQL ;
- workers asynchrones ;
- Redis facultatif mais recommandé pour jobs/locks ;
- OpenAPI générée ;
- pytest.

Les opérations IA doivent être idempotentes autant que possible.

---

# 99. SCHEMAS PARTAGÉS

Les schémas cliniques doivent exister en JSON Schema/OpenAPI.

Générer :
- types TypeScript ;
- modèles Python ;
- modèles Swift si utile.

Éviter trois définitions divergentes du même objet.

---

# 100. CONTRACT TESTS

Tester automatiquement :
- API ↔ web ;
- API ↔ iOS ;
- JSON clinique ↔ validateurs ;
- provider IA ↔ schéma strict.

---

# 101. RÉSILIENCE IA

Si extraction IA échoue :
- ne pas perdre transcription ;
- permettre retry ;
- ne pas créer un document vide comme s’il était valide.

Si génération document échoue :
- conserver Clinical Encounter Object ;
- permettre relance.

Si validation échoue :
- document = needs_review ;
- ne pas masquer l’erreur.

---

# 102. PROMPT VERSIONING

Chaque génération mémorise :
- modèle logique utilisé ;
- version du prompt ;
- version du schéma ;
- timestamp ;
- sans dupliquer inutilement le contenu patient dans la télémétrie.

Permet de reproduire les problèmes.

---

# 103. ÉVALUATION AVANT BÊTA

Étape 1 :
consultations synthétiques.

Étape 2 :
enregistrements simulés par professionnels sur patients fictifs.

Étape 3 :
shadow testing encadré juridiquement avec données réelles uniquement après validation sécurité/RGPD/HDS.

Étape 4 :
bêta limitée.

---

# 104. CRITÈRES DE SORTIE MVP

Le MVP n’est pas considéré terminé parce qu’il « génère du texte ».

Il est terminé lorsque :

- iPhone enregistre une consultation complète ;
- web enregistre une consultation complète ;
- perte réseau courte est récupérée ;
- transcript final est créé ;
- objets cliniques sont extraits ;
- dents sont normalisées ;
- négation fonctionne sur golden tests ;
- temporalité fonctionne ;
- proposé/accepté/réalisé fonctionne ;
- compte rendu est généré ;
- plan de traitement est généré ;
- au moins les templates composite/facette/usures/extraction fonctionnent ;
- provenance est consultable ;
- correction vocale met à jour l’objet clinique ;
- documents se régénèrent ;
- validation est obligatoire ;
- PDF/export texte fonctionne ;
- audio est purgé selon policy ;
- audit events fonctionnent ;
- MFA production prêt ;
- tests automatisés critiques passent.

---

# 105. CRITÈRES DE QUALITÉ AVANT UTILISATION CLINIQUE

Avant vraie pratique :
- revue sécurité ;
- revue RGPD ;
- choix infrastructure conforme ;
- contrats fournisseurs IA ;
- politique audio ;
- texte information patient ;
- procédure incident ;
- politique sauvegarde ;
- validation du niveau d’assurance clinique ;
- validation des templates par chirurgiens-dentistes ;
- test sur conditions réelles de bruit.

---

# 106. ROADMAP DE DÉVELOPPEMENT

## Milestone 0 — Fondation
- monorepo ;
- CI ;
- auth ;
- DB ;
- schémas ;
- patients ;
- encounters ;
- UI shell web/iOS ;
- fake providers.

## Milestone 1 — Capture audio
- iOS ;
- web ;
- chunks ;
- WebSocket ;
- pause/reprise ;
- reconnect ;
- session state machine.

## Milestone 2 — STT
- provider abstraction ;
- streaming ;
- final transcript ;
- diarisation ;
- dictionnaire dentaire ;
- tooth normalizer.

## Milestone 3 — Clinical Engine
- facts ;
- provenance ;
- négation ;
- temporalité ;
- corrections ;
- JSON strict ;
- tests.

## Milestone 4 — Consultation
- document generator ;
- treatment plan ;
- warnings ;
- review ;
- validation ;
- export.

## Milestone 5 — Opératoire
- composite ;
- esthétique direct ;
- facette préparation ;
- facette collage ;
- usures ;
- extraction ;
- generic minor surgery.

## Milestone 6 — Voice Correction
- commande ;
- patch clinique ;
- régénération ;
- versioning.

## Milestone 7 — Hardening
- sécurité ;
- performance ;
- offline transient ;
- audit ;
- audio purge ;
- error recovery ;
- eval suite.

## Milestone 8 — Staging clinique
- hébergement production-compatible ;
- DPA ;
- HDS/RGPD ;
- QA ;
- bêta.

---

# 107. ORDRE DE PRIORITÉ PRODUIT

Si un arbitrage temps/complexité est nécessaire :

1. exactitude clinique ;
2. absence d’invention ;
3. fiabilité audio ;
4. vitesse de validation ;
5. correction ;
6. esthétique UI ;
7. fonctions secondaires.

Ne jamais sacrifier 1–3 pour ajouter des fonctionnalités.

---

# 108. DÉFINITION DE « PARFAIT » POUR ORIS V1

Oris V1 ne cherche pas à être le logiciel du cabinet.

Il cherche à être exceptionnel sur cette boucle :

**écouter → comprendre → structurer → rédiger → vérifier → valider.**

Le produit est réussi lorsque le praticien termine une consultation esthétique, une consultation d’usure ou un acte restaurateur, et dispose presque immédiatement d’un dossier :
- fidèle ;
- propre ;
- précis ;
- cohérent ;
- modifiable ;
- traçable ;
- exploitable.

---

# 109. DÉCISIONS FIGÉES POUR LA BASCULE

- Nom : **Oris**.
- iPhone : natif.
- Desktop : web navigateur.
- Backend commun.
- Français d’abord.
- Écoute active = cœur du produit.
- Pas de logiciel de gestion complet.
- Pas d’implantologie V1.
- Pas d’IA diagnostique autonome.
- Consultation, plan de traitement et opératoire ciblé uniquement.
- Esthétique, composites, facettes et usures = domaines prioritaires.
- Extraction/minor surgery = couverture chirurgicale initiale.
- Clinical Encounter Object = source de vérité.
- Documents générés depuis cet objet.
- Correction clinique = modification de l’objet, pas seulement du texte.
- Validation praticien obligatoire.
- Audio éphémère par défaut.
- Provenance consultable.
- Architecture fournisseur IA interchangeable.
- Production : hébergement et sous-traitants adaptés aux données de santé.
- Toute donnée non dite reste non dite.

---

# 110. QUESTIONS NON BLOQUANTES POUR PLUS TARD

Ces sujets ne doivent PAS empêcher Claude Code de commencer :

- vectorisation finale du logo Oris et déclinaisons App Store ;
- fournisseur STT production ;
- fournisseur LLM production ;
- hébergeur HDS définitif ;
- wording juridique patient ;
- templates chirurgicaux additionnels exacts ;
- intégration logiciel métier ;
- modèle économique ;
- multilingue ;
- Android ;
- longueur exacte de rétention transcription ;
- signature électronique.

Ils doivent être isolés derrière configuration/interfaces lorsque nécessaire.

---

# 111. PREMIÈRE MISSION À CLAUDE CODE

Après lecture complète de ce fichier :

1. créer le repository selon l’architecture définie ;
2. créer `/docs/DECISIONS.md` avec les décisions figées ;
3. créer `/docs/IMPLEMENTATION_PLAN.md` avec les milestones 0–8 ;
4. définir les JSON Schemas :
   - ClinicalFact ;
   - ClinicalEncounter ;
   - TreatmentPlan ;
   - Procedure ;
   - Document ;
5. implémenter les modèles backend et migrations ;
6. créer un MockProvider STT et IA ;
7. implémenter un premier flux vertical synthétique :
   - patient ;
   - encounter ;
   - faux transcript ;
   - extraction mock ;
   - Clinical Encounter Object ;
   - compte rendu ;
   - plan de traitement ;
   - validation ;
8. ajouter les tests des scénarios critiques A–J ;
9. seulement ensuite brancher la capture audio réelle.

Le premier objectif n’est pas de connecter un modèle IA.
Le premier objectif est de prouver que l’architecture clinique d’Oris est cohérente de bout en bout.

---

# 112. PRINCIPE FINAL

**Oris ne doit jamais être impressionnant parce qu’il écrit beaucoup.  
Oris doit être excellent parce qu’il écrit uniquement ce qui est juste, au bon endroit, avec le bon niveau de certitude — et parce qu’il apprend continuellement de chaque correction validée sans jamais transformer l’expérience passée en faits cliniques inventés.**


---

# 113. ORIS COMME SYSTÈME APPRENANT — PRINCIPE FONDATEUR

L’amélioration continue n’est pas une fonctionnalité optionnelle d’Oris.

Elle fait partie de l’architecture du produit.

Chaque interaction utile doit pouvoir devenir un signal d’amélioration :

- correction d’une transcription ;
- correction d’un numéro de dent ;
- correction d’un terme clinique ;
- modification d’un fait extrait ;
- changement d’un statut proposé/accepté/réalisé ;
- correction d’un plan de traitement ;
- modification d’un compte rendu ;
- acceptation ou rejet d’un warning ;
- ajout d’un terme au dictionnaire ;
- préférence rédactionnelle répétée ;
- document validé sans modification ;
- document fortement corrigé ;
- échec de reconnaissance récurrent dans un environnement sonore donné.

L’objectif est double :

1. **Oris doit mieux connaître chaque praticien au fil du temps.**
2. **Oris doit globalement devenir meilleur à mesure que l’expérience produit augmente.**

Cependant, un système clinique ne doit pas modifier silencieusement ses poids, prompts ou règles en production sans validation.

L’apprentissage doit être :
- mesurable ;
- versionné ;
- explicable ;
- réversible ;
- testé avant déploiement.

---

# 114. QUATRE NIVEAUX D’APPRENTISSAGE

## Niveau 1 — Personnalisation immédiate sans réentraînement

Active dès V1.

Oris apprend progressivement les habitudes du praticien sans modifier le modèle fondamental.

Exemples :
- terminologie préférée ;
- formulations habituelles ;
- longueur des comptes rendus ;
- noms de matériaux ;
- marques utilisées ;
- termes fréquemment mal reconnus ;
- corrections phonétiques ;
- types de plans de traitement fréquents ;
- structure de documents préférée.

Cette couche doit produire un bénéfice dès les premières dizaines de consultations.

## Niveau 2 — Adaptation statistique du moteur

Oris agrège les erreurs et succès observés pour adapter :
- dictionnaires STT ;
- alias phonétiques ;
- seuils de confiance ;
- règles de normalisation ;
- règles de détection des contradictions ;
- priorités des warnings ;
- sélection de prompts ;
- routage vers des modèles spécialisés.

Aucune donnée clinique nouvelle n’est inventée.

## Niveau 3 — Amélioration contrôlée des modèles

Pipeline offline permettant :
- fine-tuning ;
- distillation ;
- entraînement d’un classifieur spécialisé ;
- amélioration d’un extracteur ;
- optimisation de prompts ;
- création d’un meilleur normaliseur dentaire.

Toute nouvelle version passe par la suite d’évaluation avant production.

## Niveau 4 — Apprentissage produit global

Oris apprend de l’usage agrégé :
- quels écrans ralentissent la validation ;
- quelles informations génèrent le plus de corrections ;
- quels templates fonctionnent ;
- quels warnings sont inutiles ;
- quels types de consultation génèrent davantage d’erreurs.

Cette couche sert à améliorer UX, workflow et modèles.

---

# 115. CE QU’ORIS NE DOIT PAS FAIRE

Interdit :

- modifier automatiquement ses poids en production après une seule consultation ;
- transformer une correction isolée en règle globale ;
- apprendre une erreur du praticien comme vérité universelle ;
- utiliser automatiquement des données patient pour entraîner un modèle sans cadre de gouvernance approprié ;
- augmenter la certitude d’un fait parce qu’un événement similaire a été observé auparavant ;
- réutiliser un fait clinique d’un patient pour compléter la consultation d’un autre patient ;
- masquer une baisse de qualité sous prétexte d’auto-apprentissage.

Le comportement clinique courant reste toujours gouverné par les données de la consultation présente.

---

# 116. LEARNING EVENT — UNITÉ DE BASE

Créer une entité `LearningEvent`.

Schéma conceptuel :

```json
{
  "learning_event_id": "uuid",
  "organization_id": "uuid",
  "user_id": "uuid",
  "encounter_id": "uuid",
  "event_type": "clinical_fact_correction",
  "scope": "user",
  "source_version": "clinical_object_v8",
  "before": {},
  "after": {},
  "reason": null,
  "confidence_before": 0.62,
  "validated_by_practitioner": true,
  "created_at": "timestamp",
  "eligible_for_global_learning": false,
  "learning_status": "captured"
}
```

Le champ `before/after` doit être structuré et minimisé.

---

# 117. TYPES DE LEARNING EVENTS

Valeurs initiales :

```text
transcript_word_correction
tooth_number_correction
speaker_role_correction
clinical_fact_added
clinical_fact_removed
clinical_fact_corrected
negation_correction
temporality_correction
certainty_correction
treatment_status_correction
treatment_sequence_correction
procedure_type_correction
material_name_correction
document_text_edit
document_section_deleted
document_section_added
warning_confirmed
warning_dismissed
glossary_term_added
style_preference_detected
document_validated_unchanged
document_validated_after_minor_edit
document_validated_after_major_edit
generation_rejected
```

Chaque type possède ses propres règles d’exploitation.

---

# 118. CLASSIFICATION DES CORRECTIONS

Toute correction doit être classée automatiquement puis éventuellement confirmée.

Classes :

## A. Correction clinique
Exemple :
26 → 27.

Doit :
- corriger l’objet clinique ;
- invalider les documents ;
- générer un LearningEvent fort.

## B. Correction sémantique non clinique
Exemple :
« restauration » → « reconstruction ».

Peut devenir préférence terminologique.

## C. Correction stylistique
Exemple :
« Le patient présente » → « Patient présentant ».

Ne doit pas modifier les faits.

## D. Correction de transcription
Exemple :
« Gényal accord » → « G-ænial A’CHORD ».

Doit enrichir le dictionnaire/alias après validation.

## E. Correction de structure
Exemple :
déplacer une information vers une autre section.

Peut améliorer le générateur documentaire.

---

# 119. MÉMOIRE PERSONNELLE DU PRATICIEN

Créer `PractitionerLearningProfile`.

Exemple :

```json
{
  "user_id": "uuid",
  "preferred_document_length": "short",
  "preferred_style": "semi_telegraphic",
  "preferred_terms": {
    "extraction": "avulsion"
  },
  "frequent_materials": [],
  "speech_aliases": [],
  "document_preferences": {},
  "confidence_overrides": {},
  "last_updated_at": "timestamp"
}
```

Cette mémoire est explicitement séparée des faits patient.

---

# 120. APPRENTISSAGE TERMINOLOGIQUE

Oris doit apprendre particulièrement bien les termes propres au praticien.

Exemple :

Le STT transcrit à plusieurs reprises :
« genial accord ».

Le praticien corrige :
« G-ænial A’CHORD ».

Après validation répétée :

```json
{
  "canonical": "G-ænial A’CHORD",
  "aliases": ["genial accord", "genial a chord"],
  "phonetic_aliases": [],
  "frequency": 14,
  "confidence": 0.98,
  "scope": "user"
}
```

Le système peut alors :
- augmenter le biais lexical STT si le fournisseur le permet ;
- corriger la transcription après STT ;
- proposer automatiquement le terme canonique.

Une première correction peut être mémorisée comme suggestion.
Une répétition augmente la confiance.

---

# 121. CONFUSION MATRIX PERSONNALISÉE

Maintenir une matrice des confusions récurrentes.

Exemples :

```text
16 ↔ 26
onlay ↔ overlay
vestibulaire ↔ buccal
G-ænial ↔ génial
IDS ↔ idée
```

La matrice sert à :
- renforcer les warnings ;
- améliorer le post-traitement ;
- demander confirmation uniquement lorsque nécessaire.

Elle ne doit jamais remplacer automatiquement une donnée clinique en cas de conflit ambigu.

---

# 122. APPRENTISSAGE DES NUMÉROS DE DENTS

Chaque correction de dent est un signal critique.

Stocker :
- mot/phrase transcrite ;
- numéro interprété ;
- numéro corrigé ;
- rôle speaker ;
- contexte lexical ;
- confiance STT ;
- contexte sonore ;
- modèle STT/version.

Construire des évaluations dédiées aux confusions :
- 16/26 ;
- 17/27 ;
- 36/46 ;
- 11/21 ;
- « deux six » / « vingt-six ».

Les corrections de dents doivent être surpondérées dans l’évaluation qualité.

---

# 123. APPRENTISSAGE DES PRÉFÉRENCES RÉDACTIONNELLES

Une modification unique ne suffit pas forcément.

Calculer une tendance.

Exemple :

Sur 20 documents :
- utilisateur supprime 18 fois « À noter que… ».

Oris doit cesser d’utiliser cette formulation.

Exemple :

Sur 15 documents :
- remplace systématiquement « extraction » par « avulsion ».

Oris propose :
> « Utiliser désormais “avulsion” par défaut ? »

Après confirmation :
préférence permanente.

Le praticien doit pouvoir voir et modifier ces préférences.

---

# 124. LEARNING CENTER — INTERFACE

Prévoir un écran futur mais architecturer dès V1 :

**Oris apprend de vous**

Sections :
- Termes appris
- Préférences rédactionnelles
- Corrections fréquentes
- Matériaux reconnus
- Règles personnelles
- Réinitialiser une préférence
- Exporter les préférences

Exemple :

```
Oris a appris :

✓ Vous préférez « avulsion » à « extraction »
✓ G-ænial A’CHORD est un composite que vous utilisez souvent
✓ Vos comptes rendus sont généralement courts
✓ Vous employez « vestibulaire » plutôt que « buccal »
```

Le système doit rester transparent.

---

# 125. ACTIVE LEARNING

Oris doit identifier les cas qui apporteraient le plus de valeur à l’amélioration.

Exemples :
- faible confiance + correction praticien ;
- forte confiance mais correction majeure ;
- dent corrigée ;
- négation corrigée ;
- proposed → performed corrigé ;
- plusieurs utilisateurs corrigent le même comportement ;
- nouveau terme inconnu fréquent.

Attribuer un `learning_priority_score`.

Concept :

```text
priority =
clinical_severity
× uncertainty
× recurrence
× model_surprise
× validation_strength
```

Les cas prioritaires alimentent le corpus d’évaluation ou d’apprentissage après gouvernance appropriée.

---

# 126. SIGNAL EXTRÊMEMENT IMPORTANT : FORTE CONFIANCE + ERREUR

Une erreur avec confiance faible est attendue.

Une erreur avec confiance très élevée est plus intéressante.

Exemple :

Oris :
26, confiance 0.97.

Praticien :
corrige en 27.

Cet événement doit :
- être marqué `high_value_learning_event` ;
- alimenter la recherche de cause ;
- créer potentiellement un cas de régression permanent.

---

# 127. VALIDATION SANS MODIFICATION = SIGNAL POSITIF

Lorsqu’un document est validé sans correction :

ne pas considérer cela automatiquement comme vérité absolue.

Mais enregistrer un signal positif faible :

- template probablement adapté ;
- extraction vraisemblablement correcte ;
- style acceptable.

Éviter de sur-apprendre à partir de simples validations rapides.

Une correction explicite possède plus de poids qu’une absence de correction.

---

# 128. SIGNAL DE REJET

Si le praticien :
- régénère plusieurs fois ;
- supprime une section entière ;
- abandonne un document ;
- revient à la transcription ;

cela doit être considéré comme un signal négatif.

Ne pas exiger qu’il remplisse un questionnaire.

L’expérience doit apprendre du comportement naturel.

---

# 129. DATA FLYWHEEL

Boucle idéale :

```text
USAGE
  ↓
CORRECTIONS / VALIDATIONS
  ↓
LEARNING EVENTS
  ↓
CURATION
  ↓
EVALUATION DATASET
  ↓
PROMPT / RULE / MODEL CANDIDATE
  ↓
OFFLINE EVALUATION
  ↓
SHADOW TESTING
  ↓
CANARY RELEASE
  ↓
PRODUCTION
  ↓
MONITORING
  ↓
NOUVEL USAGE
```

Cette boucle doit faire partie de l’infrastructure produit.

---

# 130. DATASET REGISTRY

Créer une gestion versionnée des jeux de données.

Entité `DatasetVersion` :

```json
{
  "dataset_id": "clinical_extraction_fr",
  "version": "2026.09.1",
  "created_at": "timestamp",
  "case_count": 1250,
  "source_breakdown": {},
  "domains": [
    "aesthetic",
    "wear",
    "composite",
    "veneer",
    "minor_surgery"
  ],
  "hash": "...",
  "approved_for_eval": true,
  "approved_for_training": false
}
```

Différencier strictement :
- dataset de développement ;
- dataset de training ;
- dataset de validation ;
- dataset de test verrouillé.

---

# 131. TEST SET VERROUILLÉ

Le test clinique principal ne doit jamais être utilisé pour optimiser directement le modèle.

Objectif :
éviter l’illusion de progrès par sur-apprentissage.

Créer :
- `development_set`
- `regression_set`
- `locked_clinical_test_set`.

Les résultats du locked set sont historisés par version.

---

# 132. PATIENT-LEVEL SPLITTING

Lorsqu’un corpus réel est autorisé :

ne jamais mettre des données issues du même patient dans train et test.

Lorsque possible :
séparer également par praticien pour certains benchmarks.

Objectif :
mesurer la généralisation réelle.

---

# 133. DÉDUPLICATION

Avant entraînement :
- déduplication exacte ;
- déduplication quasi-sémantique ;
- détection des templates répétitifs ;
- éviter qu’un même exemple apparaisse sous plusieurs versions.

---

# 134. CORPUS SYNTHÉTIQUE

Maintenir un corpus synthétique très large.

Avantages :
- zéro donnée patient ;
- génération ciblée des cas rares ;
- tests adversariaux ;
- bruit ;
- accents ;
- corrections ;
- négations ;
- contradictions.

Mais le corpus synthétique ne doit pas remplacer entièrement les évaluations réalistes.

---

# 135. ADVERSARIAL DATA GENERATION

Générer automatiquement des scénarios difficiles :

- « la 26, non la 27 » ;
- « je pensais 16 mais finalement 15 » ;
- longues digressions ;
- patient qui emploie une mauvaise terminologie ;
- assistante qui cite un autre patient ;
- médicament nié ;
- traitement passé ;
- phrases interrompues ;
- bruit turbine ;
- noms commerciaux ;
- homophones ;
- accents régionaux ;
- débit rapide.

Ces scénarios enrichissent en continu la suite de tests.

---

# 136. MODEL REGISTRY

Toute version d’un composant IA doit être enregistrée.

`ModelVersion` :

```json
{
  "component": "clinical_extractor",
  "version": "3.4.1",
  "base_model": "...",
  "prompt_version": "p27",
  "schema_version": "12",
  "training_dataset_version": "2026.10.2",
  "eval_report_id": "uuid",
  "release_status": "candidate"
}
```

---

# 137. PROMPT REGISTRY

Les prompts sont du code.

Ils doivent :
- être versionnés ;
- avoir un changelog ;
- avoir des tests ;
- avoir des métriques ;
- être rollbackables.

Aucun prompt de production ne doit être modifié directement depuis une console sans versioning.

---

# 138. RULE REGISTRY

Les règles déterministes doivent également être versionnées.

Exemples :
- tooth normalization ;
- negation resolver ;
- material canonicalizer ;
- temporal resolver.

Chaque modification doit pouvoir être reliée aux cas ayant motivé le changement.

---

# 139. AUTOMATED EVAL PIPELINE

À chaque candidat :

1. exécuter unit tests ;
2. golden tests ;
3. regression set ;
4. locked test si étape de release ;
5. tests de latence ;
6. tests de coût ;
7. tests de format JSON ;
8. tests de sécurité ;
9. comparaison avec version production.

Produire un rapport automatique.

---

# 140. GATE DE DÉPLOIEMENT

Une nouvelle version ne doit pas être déployée seulement parce que la moyenne globale augmente.

Bloquer si elle régresse sur des critères critiques :

- Tooth Number Accuracy ;
- Negation Accuracy ;
- Plan-vs-Performed Accuracy ;
- Unsupported Statement Rate ;
- Critical Error Rate.

Même si le style général est meilleur.

---

# 141. PONDÉRATION DES ERREURS

Toutes les erreurs ne valent pas la même chose.

Exemple de pondération :

```text
mauvaise dent                     100
performed au lieu de proposed     100
négation inversée                 100
médicament actuel erroné           90
diagnostic certain vs hypothèse    90
matériau erroné opératoire         70
omission clinique secondaire       30
style                              5
ponctuation                        1
```

Ces valeurs sont configurables après validation clinique.

Utiliser un score de risque pondéré en plus des métriques classiques.

---

# 142. SHADOW MODE

Avant remplacement d’un modèle en production :

la nouvelle version peut traiter silencieusement une copie du même flux sans affecter la sortie utilisateur.

Comparer :
- production ;
- candidate.

Mesurer :
- faits différents ;
- corrections potentielles ;
- erreurs critiques ;
- latence ;
- coût.

Aucune sortie shadow ne modifie le dossier patient.

---

# 143. CANARY RELEASE

Déployer progressivement :

- utilisateurs internes ;
- petite cohorte ;
- pourcentage limité ;
- extension graduelle.

Possibilité de rollback immédiat.

---

# 144. A/B TESTS — LIMITES

A/B possible sur :
- UX ;
- style ;
- emplacement des boutons ;
- présentation des warnings.

Pour des fonctions cliniques à risque :
préférer shadow/canary contrôlé plutôt qu’un A/B naïf.

---

# 145. AUTO-ROUTING DES MODÈLES

Oris peut apprendre qu’un seul modèle n’est pas optimal pour tout.

Future architecture :

```text
consultation esthétique → extractor A
composite opératoire → extractor B
chirurgie → extractor C
correction vocale → model léger D
validation factuelle → validator E
```

Un routeur choisit le modèle adapté.

Ce routage doit être mesuré et versionné.

---

# 146. ENSEMBLE / DOUBLE LECTURE POUR POINTS CRITIQUES

Pour certains faits à haut risque :
- numéro de dent ;
- négation ;
- acte réalisé ;
- médicament ;

Oris peut combiner :
- STT ;
- extracteur ;
- règle ;
- second validateur.

En cas de désaccord :
warning plutôt que décision silencieuse.

---

# 147. SELF-CRITIQUE CONTRÔLÉE

Une passe de validation peut demander à un modèle distinct :

- quelles affirmations ne sont pas supportées ?
- y a-t-il une augmentation de certitude ?
- le document transforme-t-il un projet en acte réalisé ?
- existe-t-il une incohérence dentaire ?

Cette passe n’ajoute jamais de nouveau fait.
Elle peut seulement :
- valider ;
- signaler ;
- retirer ;
- demander régénération.

---

# 148. APPRENTISSAGE DES WARNINGS

Oris doit apprendre les warnings utiles.

Si un praticien ignore systématiquement un warning non critique :
le système peut réduire sa priorité.

Mais certains warnings restent non désactivables :
- dent ambiguë ;
- négation critique ;
- perte audio ;
- proposed/performed conflict ;
- information importante contradictoire.

---

# 149. FEEDBACK EXPLICITE ULTRA-RAPIDE

Ne jamais imposer de formulaire long.

Ajouter seulement lorsque pertinent :

👍 Correct  
👎 À corriger

Pour un point spécifique.

Ou :
**Pourquoi ?**
- mauvaise dent ;
- mauvais terme ;
- information inventée ;
- information manquante ;
- mauvais statut ;
- autre.

Facultatif.

---

# 150. ROOT CAUSE ANALYSIS AUTOMATIQUE

Pour les erreurs répétées, Oris doit pouvoir produire un rapport interne :

Exemple :

```text
Cluster : confusion 16 / 26
Occurrences : 37
STT provider : X
Model version : 2.8
Contexte : phrase courte isolée
Confiance moyenne : 0.91
Praticiens touchés : 8
Impact : critique
```

Permet de choisir la bonne intervention :
- STT ;
- normalisation ;
- prompt ;
- warning ;
- modèle.

---

# 151. ERROR CLUSTERING

Créer automatiquement des clusters d’erreurs similaires avec embeddings sur des représentations minimisées et gouvernées.

Exemples :
- termes matériaux ;
- numéros de dents ;
- négation ;
- futurs ;
- facettes ;
- usures.

Le clustering sert au produit, pas directement au dossier patient.

---

# 152. DASHBOARD QUALITÉ INTERNE

Construire un dashboard non clinique :

- Critical Error Rate ;
- corrections / 100 consultations ;
- Tooth Accuracy ;
- Negation Accuracy ;
- Plan vs Performed ;
- hallucinations détectées ;
- latence ;
- coût ;
- version models/prompts ;
- tendances par release ;
- top clusters d’erreur.

Aucune identité patient affichée.

---

# 153. SCORE D’AMÉLIORATION PAR VERSION

Chaque release IA reçoit un rapport :

```text
Clinical extraction +2.8%
Tooth accuracy +0.7%
Negation unchanged
Unsupported statements -18%
Latency +220 ms
Cost -5%
Critical regressions: 0
```

Cette logique rend le progrès objectivable.

---

# 154. APPRENTISSAGE LOCAL VS GLOBAL

## Local
Applicable uniquement au praticien/organisation.

Exemples :
- style ;
- matériaux ;
- noms ;
- vocabulaire ;
- templates ;
- raccourcis.

## Global
Applicable potentiellement à tous.

Exemple :
un défaut général de reconnaissance de « overlay ».

Une correction locale ne devient jamais automatiquement globale.

Il faut un processus de promotion.

---

# 155. PROMOTION D’UNE RÈGLE LOCALE

Pipeline :

```text
local observation
→ repeated signal
→ multi-user confirmation
→ curated candidate
→ eval
→ global release
```

Possibilité d’intervention humaine à chaque étape.

---

# 156. CONFLICT RESOLUTION

Si deux utilisateurs ont des préférences différentes :

ne pas chercher à les fusionner.

Exemple :
A préfère « avulsion ».
B préfère « extraction ».

Conserver deux profils locaux.

Le moteur global doit rester neutre.

---

# 157. LEARNING PRIVACY MODES

Prévoir trois politiques configurables.

## Mode A — Strict
- données uniquement pour fournir le service ;
- personnalisation locale/configuration ;
- pas de réutilisation pour dataset global.

## Mode B — Improvement
- événements minimisés et autorisés peuvent contribuer à l’amélioration contrôlée.

## Mode C — Research/Advanced
- uniquement si un cadre dédié le permet ;
- éventuelle conservation de certains exemples pour amélioration avancée.

La définition juridique et contractuelle exacte doit être validée avant commercialisation.

---

# 158. AUDIO ET APPRENTISSAGE

Par défaut :
audio éphémère.

Conséquence :
les améliorations STT globales ne peuvent pas automatiquement conserver tous les audios.

Architecture :
- apprentissage à partir des corrections textuelles sans audio ;
- possibilité future de conserver uniquement des extraits explicitement sélectionnés/éligibles selon gouvernance ;
- séparation complète entre stockage clinique normal et corpus de recherche/qualité.

Ne jamais empêcher la purge audio parce qu’Oris « pourrait en avoir besoin pour apprendre ».

---

# 159. DE-IDENTIFICATION / MINIMISATION

Avant qu’un cas puisse entrer dans un corpus d’amélioration :

processus dédié de minimisation.

Retirer lorsque possible :
- nom ;
- prénom ;
- date de naissance ;
- adresse ;
- téléphone ;
- email ;
- identifiants ;
- noms de proches ;
- informations non nécessaires à la tâche.

Pseudonymisation/dé-identification doit être traitée comme un pipeline séparé et auditable.

---

# 160. DATA LINEAGE

Pour chaque exemple d’apprentissage/évaluation, pouvoir répondre :

- d’où vient-il ?
- quelle autorisation/politique s’applique ?
- quelles transformations ont été réalisées ?
- qui l’a validé ?
- dans quels datasets est-il présent ?
- quelles versions de modèle l’ont utilisé ?

Créer une traçabilité de dataset.

---

# 161. RIGHT TO EXCLUDE

Le système doit pouvoir retirer un exemple de tous les futurs datasets lorsqu’il n’est plus éligible.

Cela nécessite :
- IDs stables ;
- lineage ;
- dataset manifests ;
- capacités de rebuild.

---

# 162. NO TRAINING FROM RAW PRODUCTION BY DEFAULT

Le backend de production ne doit pas envoyer automatiquement les consultations vers une pipeline de fine-tuning.

Le pipeline learning est séparé.

Architecture :

```text
PRODUCTION
   ↓
eligible learning events
   ↓
GOVERNANCE GATE
   ↓
CURATED LEARNING STORE
   ↓
TRAINING / EVALUATION
```

---

# 163. HUMAN-IN-THE-LOOP POUR LA QUALITÉ

Les exemples cliniques à fort impact doivent pouvoir être revus par des professionnels autorisés.

Outils internes :
- source ;
- sortie ;
- correction ;
- catégories d’erreur ;
- validation ;
- commentaire.

Ne pas exposer plus de données que nécessaire.

---

# 164. EXPERT REVIEW SET

Créer un set évalué par chirurgiens-dentistes.

Domaines V1 :
- esthétique ;
- composite ;
- facettes ;
- usures ;
- chirurgie mineure.

Pour chaque cas :
- faits attendus ;
- éléments explicitement absents ;
- statut ;
- certitude ;
- document acceptable.

---

# 165. INTER-RATER AGREEMENT

Pour certains benchmarks, plusieurs dentistes annotent les mêmes cas.

Mesurer les désaccords humains.

Objectif :
ne pas pénaliser Oris pour une formulation clinique où les experts eux-mêmes ne sont pas d’accord, tout en maintenant les règles factuelles strictes.

---

# 166. PERSONALIZATION CONFIDENCE

Chaque préférence personnelle possède :
- nombre d’observations ;
- force ;
- date ;
- source ;
- confirmation explicite éventuelle.

Exemple :

```json
{
  "preference": "use_avulsion",
  "observations": 12,
  "confidence": 0.96,
  "explicitly_confirmed": true
}
```

---

# 167. DECAY DES PRÉFÉRENCES

Une habitude peut changer.

Prévoir :
- pondération plus forte des usages récents ;
- possibilité d’oublier une préférence ;
- possibilité de revenir au défaut.

Une préférence confirmée explicitement ne doit pas disparaître automatiquement sans signal contraire.

---

# 168. AUTO-CREATION DE GLOSSAIRE

Si le praticien corrige plusieurs fois le même terme :

Oris propose automatiquement :
> Ajouter « X » à votre vocabulaire Oris ?

Un clic suffit.

À terme :
ajout automatique pour des corrections répétées à forte confiance, selon préférence utilisateur.

---

# 169. ADAPTATION AU STYLE VOCAL

Le système peut apprendre des patterns personnels de dictée/conversation :

- « la deux six » ;
- « sur onze et vingt-et-un » ;
- abréviations orales ;
- noms de matériaux ;
- habitudes linguistiques.

Cette couche sert uniquement à améliorer transcription et extraction.

Elle ne doit pas inférer de caractéristiques personnelles inutiles.

---

# 170. ADAPTATION AU CABINET

Niveau organisation :
- liste de matériaux ;
- confrères ;
- laboratoires ;
- terminologie ;
- templates ;
- marques ;
- préférences administratives.

Un nouvel utilisateur du même cabinet peut hériter de la base organisationnelle sans hériter du style personnel d’un praticien.

---

# 171. ROUTING PAR CONFIDENCE

Lorsque confiance haute :
pipeline standard.

Lorsque confiance faible :
- second pass ;
- modèle plus puissant ;
- validation croisée ;
- warning.

Le système apprend à réserver les ressources coûteuses aux cas difficiles.

Objectif :
qualité maximale avec coût maîtrisé.

---

# 172. COST-AWARE LEARNING

Mesurer pour chaque pipeline :
- coût ;
- latence ;
- précision ;
- erreurs critiques.

Oris peut apprendre qu’un modèle léger suffit pour :
- reformulation stylistique.

Et qu’un modèle plus puissant est nécessaire pour :
- résolution de contradictions cliniques.

Optimiser sans dégrader les métriques critiques.

---

# 173. AUTO-EVAL DES NOUVELLES DONNÉES

À intervalles réguliers :
- extraire de nouveaux scénarios synthétiques à partir des clusters d’erreur ;
- ajouter des cas de régression ;
- recalculer les métriques ;
- générer un rapport.

Ainsi, la suite de tests s’améliore même avant un nouvel entraînement.

---

# 174. REGRESSION CASE FOREVER

Toute erreur critique confirmée doit pouvoir devenir un cas permanent de régression.

Exemple :
une confusion 26/27 ayant produit un mauvais CR.

Créer un scénario anonymisé/synthétisé équivalent.

Principe :
**une erreur grave corrigée une fois ne doit idéalement jamais revenir silencieusement.**

---

# 175. CONTINUAL BENCHMARK

Maintenir un benchmark temporel.

Exemple :

```text
v1.0
critical error rate 2.1%
tooth accuracy 96.4%

v1.4
critical error rate 1.2%
tooth accuracy 98.1%

v2.0
critical error rate 0.7%
tooth accuracy 99.0%
```

Permet de vérifier qu’Oris progresse réellement.

---

# 176. FEEDBACK SUR L’APPRENTISSAGE POUR L’UTILISATEUR

L’apprentissage doit être perceptible.

Exemples :
- « Oris a appris ce terme. »
- « Préférence enregistrée. »
- « Cette correction améliorera désormais vos prochains comptes rendus. »

Éviter :
messages permanents ou intrusifs.

---

# 177. ANNULER CE QU’ORIS A APPRIS

Interface permettant :
- retirer un terme ;
- réinitialiser le style ;
- supprimer une règle locale ;
- désactiver une préférence.

Chaque apprentissage utilisateur doit être réversible.

---

# 178. EXPLICATION D’UNE PERSONNALISATION

Exemple :

> Pourquoi Oris écrit “avulsion” ?
>
> Vous avez remplacé “extraction” par “avulsion” dans 12 comptes rendus et confirmé cette préférence le 4 octobre.

Cette transparence augmente la confiance.

---

# 179. APPRENTISSAGE DU PLAN DE TRAITEMENT

Oris peut apprendre la présentation du plan, jamais décider du traitement.

Peut apprendre :
- niveau de détail ;
- vocabulaire ;
- organisation préférée ;
- format phases/étapes ;
- présentation patient.

Ne doit jamais apprendre :
« pour ce type de patient, proposer automatiquement X » à partir des habitudes passées.

Les choix thérapeutiques restent explicitement issus de la consultation/praticien.

---

# 180. APPRENTISSAGE OPÉRATOIRE

Particulièrement utile pour les actes répétitifs.

Oris apprend :
- noms de matériaux habituels ;
- ordre rédactionnel ;
- termes préférés ;
- éléments habituellement dictés ;
- erreurs STT.

Mais un matériau fréquemment utilisé ne doit jamais être inséré si non mentionné lors de l’acte.

Exemple :
le praticien utilise G-ænial A’CHORD dans 90 % des cas.

Audio actuel :
« composite réalisé sur 11 ».

Oris ne doit PAS écrire G-ænial A’CHORD.

La fréquence améliore la reconnaissance, pas l’invention.

---

# 181. APPRENTISSAGE DES INFORMATIONS MANQUANTES

Oris peut apprendre qu’un praticien souhaite être alerté lorsque certaines informations ne sont pas dites.

Exemple :
dans un CR facettes, le praticien juge important :
- isolation ;
- matériau de collage ;
- contrôle occlusal.

Oris peut signaler :
« Non documenté ».

Il ne les remplit pas.

---

# 182. PERSONALIZED WARNING PROFILE

Chaque warning :
- mandatory_global ;
- recommended_global ;
- user_configurable.

Exemple :

`tooth_ambiguity` = mandatory_global.

`shade_missing` = user_configurable.

---

# 183. AUTO-OPTIMISATION DES PROMPTS

Permise uniquement offline.

Pipeline possible :
- générer variantes ;
- tester automatiquement ;
- éliminer celles qui régressent ;
- sélectionner candidats ;
- revue ;
- shadow ;
- release.

Jamais :
prompt évoluant en direct dans le service de production sans tests.

---

# 184. MODEL FINE-TUNING

Future option lorsque les données et volumes le justifient.

Candidats :
- extracteur clinique ;
- normaliseur terminologique ;
- routeur ;
- correction de transcription ;
- classifieur de document.

La génération documentaire pourrait rester sur un modèle général avec contraintes fortes tant que cela donne de meilleurs résultats.

Ne fine-tuner que lorsqu’une amélioration mesurable justifie la complexité.

---

# 185. SPECIALIZED SMALL MODELS

À terme, utiliser des petits modèles dédiés peut être pertinent pour :
- reconnaître dent/surface ;
- classer assertion ;
- classer temporalité ;
- détecter proposed/performed ;
- classifier les commandes vocales.

Avantages :
- latence ;
- coût ;
- déterminisme ;
- possibilité d’évaluation précise.

---

# 186. RETRIEVAL DE CONNAISSANCES

Une base de connaissances peut aider aux définitions, dictionnaires et schémas.

Mais elle ne doit pas ajouter de faits au dossier.

Deux couches distinctes :

```text
clinical evidence = ce qui a été dit / saisi
domain knowledge = ce que le système sait en général
```

Seule la première peut affirmer qu’un événement s’est produit chez le patient.

---

# 187. APPRENTISSAGE MULTI-MODAL FUTUR

Préparer l’architecture, mais ne pas activer en V1 :

- photo clinique ;
- scan ;
- radiographie ;
- vidéo.

Toute future analyse doit avoir ses propres validations, provenance et règles.

---

# 188. QUALITY INCIDENT LOOP

Pour une erreur critique remontée :

1. créer incident ;
2. identifier version ;
3. reproduire ;
4. créer test ;
5. déterminer root cause ;
6. corriger ;
7. exécuter regression suite ;
8. shadow ;
9. release ;
10. fermer incident.

Chaque incident critique contribue à rendre Oris plus robuste.

---

# 189. USER-REPORTED ERROR BUTTON

Sur chaque document :

**Signaler un problème Oris**

Catégories :
- mauvaise dent ;
- information inventée ;
- information manquante ;
- mauvais sens ;
- mauvaise formulation ;
- autre.

Le signal doit automatiquement embarquer les IDs/version nécessaires, sans nécessiter que l’utilisateur rédige un rapport technique.

---

# 190. RELEASE NOTES IA INTERNES

Chaque release documente :

- ce qui a changé ;
- pourquoi ;
- métriques ;
- risques ;
- known limitations ;
- rollback plan.

---

# 191. ROLLBACK

Tout composant apprenant doit être rollbackable rapidement :

- modèle ;
- prompt ;
- rule set ;
- glossary global ;
- routing policy.

Ne pas déployer un mécanisme d’apprentissage qu’on ne peut pas annuler.

---

# 192. FEATURE STORE / LEARNING STORE

Séparer :
- base clinique de production ;
- préférences utilisateur ;
- learning events ;
- datasets d’évaluation ;
- datasets d’entraînement.

Éviter une table géante mélangeant tout.

---

# 193. DATA RETENTION DU LEARNING STORE

La rétention doit être configurée séparément de celle du dossier clinique.

Les règles exactes dépendront de la gouvernance et du cadre juridique retenus.

Le système doit être capable de :
- purger ;
- exclure ;
- reconstruire des datasets ;
- prouver les versions.

---

# 194. MONITORING DU DRIFT

Surveiller :
- nouveaux termes ;
- changement distribution des actes ;
- évolution des erreurs ;
- nouvelles versions STT ;
- changements fournisseur ;
- accents/environnements nouveaux ;
- performance par domaine.

Une baisse progressive doit être détectée avant que les utilisateurs ne la signalent massivement.

---

# 195. SEGMENTED QUALITY METRICS

Ne jamais se contenter d’une moyenne globale.

Mesurer par :
- esthétique ;
- composite ;
- facettes ;
- usures ;
- chirurgie ;
- longueur consultation ;
- qualité audio ;
- iPhone/web ;
- provider STT ;
- version modèle.

Une amélioration globale ne doit pas masquer une régression sur les facettes.

---

# 196. FAIRNESS TECHNIQUE DE RECONNAISSANCE

Tester sur diversité de :
- voix ;
- débits ;
- accents francophones ;
- sexe vocal ;
- environnement sonore.

Objectif :
le système ne doit pas être excellent uniquement pour les voix présentes dans les premiers jeux de test.

---

# 197. SELF-IMPROVEMENT KPI

Ajouter au dashboard interne :

## Learning Velocity
temps moyen entre :
- identification d’un cluster d’erreur ;
- correctif validé en production.

## Recurrence Rate
pourcentage d’erreurs déjà connues réapparaissant après correctif.

## Personalization Benefit
réduction du taux de correction d’un utilisateur après X consultations.

## Global Improvement Rate
progression des métriques cliniques sur plusieurs releases.

---

# 198. CIBLE DE PERSONNALISATION

Après environ 20–50 consultations d’un praticien, Oris devrait idéalement montrer une amélioration mesurable sur :
- vocabulaire ;
- matériaux ;
- style ;
- erreurs phonétiques ;
- corrections récurrentes.

Ce chiffre est un objectif produit à mesurer, pas une garantie.

---

# 199. CIBLE D’AMÉLIORATION GLOBALE

Chaque cycle de release IA doit :
- réduire au minimum une catégorie d’erreur significative ;
- ne créer aucune régression critique connue ;
- augmenter ou maintenir les métriques critiques.

---

# 200. ROADMAP LEARNING

## Phase L0 — Dès le premier prototype
- versioning prompts/models ;
- LearningEvent schema ;
- correction diff ;
- golden tests ;
- audit des versions.

## Phase L1 — MVP
- profil praticien ;
- dictionnaire personnalisé ;
- préférences ;
- auto-apprentissage terminologique ;
- learning events ;
- dashboard qualité de base.

## Phase L2 — Bêta
- active learning ;
- clusters d’erreur ;
- regression generation ;
- shadow mode ;
- model registry ;
- dataset registry.

## Phase L3 — Production mature
- fine-tuning ciblé ;
- automatic candidate evaluation ;
- canary releases ;
- model routing ;
- drift monitoring ;
- learning analytics avancés.

---

# 201. NOUVELLE DÉFINITION DU CŒUR ORIS

Oris n’est pas seulement :

**écouter → comprendre → structurer → documenter**

Il doit devenir :

**écouter → comprendre → structurer → documenter → observer les corrections → apprendre → s’améliorer → recommencer**

Tout en gardant un principe immuable :

**l’apprentissage peut améliorer la reconnaissance et la rédaction ; il ne doit jamais inventer la réalité clinique.**

---

# 202. NOUVELLES INSTRUCTIONS À CLAUDE CODE — LEARNING FIRST

Claude Code doit intégrer dès la fondation :

1. `LearningEvent` ;
2. `PractitionerLearningProfile` ;
3. `ModelVersion` ;
4. `PromptVersion` ;
5. `DatasetVersion` ;
6. `EvaluationRun` ;
7. versioning des règles ;
8. système de diff avant/après correction ;
9. télémétrie sans données de santé dans les logs ;
10. golden/regression tests ;
11. capacité future de shadow mode.

Même si certaines fonctions ne sont pas exposées dans l’interface V1.

Il ne faut surtout pas construire une V1 non apprenante puis tenter d’ajouter ces mécanismes plus tard.

L’amélioration continue doit être native à l’architecture.


---

# 203. HIÉRARCHIE DES SOURCES DE VÉRITÉ

En cas de divergence pendant le développement, appliquer cet ordre :

1. `ORIS_MASTER_SPEC_V1_2.md` — vision, périmètre et règles cliniques ;
2. `schemas/*.json` — contrats machine-readable ;
3. `docs/DECISIONS.md` — décisions figées ;
4. `docs/ACCEPTANCE_CRITERIA.md` — critères de sortie ;
5. `docs/DESIGN_SYSTEM.md` — interface et design ;
6. `docs/IMPLEMENTATION_PLAN.md` — ordre de réalisation ;
7. `docs/BACKLOG.md` — détail des tâches.

Claude Code ne doit pas résoudre une contradiction par intuition : il doit signaler la divergence dans `docs/KNOWN_LIMITATIONS.md` et privilégier la source la plus haute dans cette hiérarchie.

---

# 204. IDENTITÉ VISUELLE FIGÉE POUR V1

Nom produit : **Oris**.

Concept iconographique :
- contour ouvert évoquant discrètement une dent ;
- onde/parole au centre ;
- forme simple lisible à petite taille ;
- aucun pictogramme de dent littéral ou cartoon.

Palette V1 :
- Deep Blue `#0F2D46` ;
- Oris Blue `#3B82F6` ;
- Misty Teal `#7DD3C7` ;
- Cloud `#EAF1F6` ;
- Graphite `#1F2937` ;
- White `#FFFFFF`.

Direction : clinique premium, calme, très lumineuse, précise, sans esthétique de chatbot.

Le fichier `docs/DESIGN_SYSTEM.md` et `design/tokens.json` sont les références d’implémentation.

---

# 205. FRONTIÈRE ENTRE V1 CLINIQUE ET INFRASTRUCTURE D’APPRENTISSAGE

Doit être implémenté dès la fondation :
- LearningEvent ;
- diff avant/après correction ;
- PractitionerLearningProfile ;
- PromptVersion / ModelVersion ;
- golden tests ;
- dictionnaire personnel ;
- préférences explicites ;
- journalisation des corrections structurées.

Ne doit pas retarder le premier vertical slice :
- fine-tuning ;
- clustering automatisé à grande échelle ;
- canary release automatisée ;
- auto-optimisation de prompts ;
- dashboard MLOps avancé ;
- routage multi-modèles sophistiqué.

Ces capacités doivent avoir des interfaces et des tables prévues, mais peuvent rester inactives derrière feature flags jusqu’aux phases Learning L2/L3.

---

# 206. STRATÉGIE FOURNISSEURS IA / STT

Le choix fournisseur n’est pas figé dans la V1.2.

Claude Code doit :
1. implémenter les interfaces fournisseurs ;
2. utiliser des mocks pour le premier vertical slice ;
3. rendre les fournisseurs sélectionnables par configuration ;
4. exécuter le banc d’essai défini dans `docs/TECHNICAL_BENCHMARK.md` avant choix production ;
5. interdire toute dépendance au fournisseur dans les objets métier.

Le choix production doit être fondé sur le corpus Oris réel/synthétique et non sur des benchmarks marketing génériques.

---

# 207. FREEZE DE BASCULE VERS CLAUDE CODE

À compter de cette version :
- le périmètre V1 est gelé ;
- les nouvelles idées sont ajoutées au backlog V1.x/V2 sans modifier le cœur V1 ;
- toute modification de règle clinique exige un test ;
- toute nouvelle fonctionnalité exige un critère d’acceptation ;
- toute modification de schéma exige une migration et une version ;
- toute modification de prompt exige un PromptVersion ;
- toute modification du moteur d’extraction exige un EvaluationRun.

Le premier objectif de Claude Code est un vertical slice entièrement synthétique et testable, puis la capture audio réelle.
