# Concurrence et benchmark fonctionnel — Oris

*Recherche menée le 26 septembre 2026. Sources en fin de document.*

**Avertissement de méthode.** Tout ce qui suit vient de sites d'éditeurs, d'articles de
presse professionnelle et de comparatifs en ligne. Les chiffres d'usage (« 4 000
praticiens », « 10 000 dentistes ») et les promesses de gain de temps sont des
**annonces d'éditeurs**, jamais des mesures indépendantes. Les prix sont ceux affichés
publiquement en septembre 2026 et changent vite. Aucun de ces produits n'a été essayé :
ce document compare des **fonctions annoncées**, pas des qualités constatées.

---

## 1. La carte du terrain

L'IA au cabinet dentaire se répartit en quatre familles qui ne se concurrencent pas
vraiment entre elles :

| Famille | Ce qu'elle fait | Acteurs |
|---|---|---|
| **Documentation clinique** (la nôtre) | Écouter ou dicter, produire le compte rendu et les courriers | Askara, Kiroku, Bola AI, Denti.AI, DentScribe, VoiceboxMD, Doctolib, Nabla, Abridge, Heidi… |
| **Imagerie** | Lire la radio, détecter caries et os, montrer au patient | Allisone (FR), Overjet, Pearl, VideaHealth, Denti.AI |
| **Accueil téléphonique** | Répondre, trier, prendre le rendez-vous | DentalCall IA, Recept AI, Doctolib Assistant téléphonique |
| **Logiciel de gestion** | Agenda, dossier, devis, facturation, télétransmission | Julie, Logosw, Desmos, Veasy, Matisse, Dental Pilote… qui ajoutent tous des briques IA |

**Oris joue dans la première case, uniquement.** C'est un choix : aucun concurrent
sérieux n'est bon dans les quatre. Mais cela veut aussi dire qu'Oris vit **à côté** du
logiciel de gestion du cabinet, et que la question de la passerelle finira par se poser
(§5).

---

## 2. France

### 2.1 Askara — le concurrent frontal

C'est le produit le plus proche d'Oris sur le marché français : solution française, IA
dédiée aux chirurgiens-dentistes, centrée sur la documentation clinique.

- **Active Consult** : écoute la consultation en direct, sans dictée, et produit les
  documents — comptes rendus, courriers, ordonnances, fiches labo, comptes rendus de
  cone beam. Neuf types de documents annoncés.
- **Dictaphone IA** : notes vocales transformées en document « en 50 secondes ».
- **Fiche patient auto-remplie** depuis Active Consult.
- **Agent conversationnel** : interroger sa base à la voix.
- **Pilotage du cabinet** : statistiques patients, devis, marges.
- En déploiement progressif : agenda, devis automatiques depuis le plan de traitement,
  feuilles de soins et télétransmission.
- S'est ouvert à l'orthodontie ; intégré au réseau Global D côté ortho.
- **Hébergement France, HDS et RGPD annoncés, ISO 27001, IA propriétaire** (l'éditeur
  insiste sur le fait de ne pas passer par ChatGPT/OpenAI).
- **Prix public : 43 à 129 €/mois.** L'écoute de consultation (Active Consult) exige le
  plan Premium à **129 €/mois**. Remise ~23 % à l'année, tarif dégressif à partir de
  deux praticiens, secrétaires incluses sans surcoût.
- Annoncé : 4 000+ praticiens inscrits, 300 000+ documents générés, 4,6/5 Trustpilot.
- **Limites relevées par la presse spécialisée** : ne gère ni agenda, ni facturation, ni
  télétransmission (au moment de l'article) ; efficacité dépendante de la compatibilité
  avec le logiciel métier ; validation humaine obligatoire.

> **Ce qu'il faut en retenir :** Askara a deux ans d'avance sur la couverture
> documentaire (ordonnances, fiches labo, devis, cone beam) et sur la distribution.
> Il ne publie en revanche **aucun mécanisme de traçabilité fait-par-fait** : on ne
> trouve nulle part l'équivalent de la règle « chaque phrase s'appuie sur un segment
> cité ». C'est notre angle.

### 2.2 Doctolib — Assistant de consultation

- Lancé en octobre 2024, **plus de 6 millions de consultations** passées fin 2025 ;
  ouverture aux hôpitaux et aux praticiens qui n'ont que l'agenda.
- Écoute la consultation, produit une note classée automatiquement, dictée intégrée.
- **79 €/mois**, en plus de l'abonnement Doctolib.
- Cible affichée : médecins et sages-femmes (kinésithérapeutes explicitement exclus).
  **Les chirurgiens-dentistes ne sont pas la cible de l'assistant de consultation** ;
  c'est l'**Assistant téléphonique** que Doctolib a ouvert aux dentistes, avec un
  déploiement élargi annoncé pour 2026.
- **Le vrai risque concurrentiel n'est pas fonctionnel, il est commercial :** Doctolib
  est déjà installé dans les cabinets et peut ouvrir l'assistant de consultation aux
  dentistes quand il le décide.

### 2.3 Allisone — imagerie (voisin, pas concurrent)

Start-up française (2021), **marquage CE médical**, levée de 10 M€. Analyse la
radiographie, détecte les lésions, les met en évidence pour le patient, aide à poser le
plan de traitement ; intégré à Desmos (Juxta). Adhésion au plan de traitement en hausse
de 24 % annoncée. Évaluée dans un projet Health Data Hub.

**Pourquoi c'est important pour nous :** Allisone est un **dispositif médical**, Oris
non — et ne doit pas le devenir tant qu'il ne pose pas de diagnostic (§6). Allisone est
plutôt un partenaire naturel qu'un rival : la radio d'un côté, la parole de l'autre.

### 2.4 Le reste du paysage français

- **DentalCall IA**, **Recept AI** : standard téléphonique IA, HDS/RGPD annoncés.
- **La Fraise** : devis et prédiction de remboursement.
- **DentalIAssist**, **Matisse**, **Dental Pilote** : logiciels de gestion qui ajoutent
  des briques IA (questionnaire, plan de traitement, transcription, rappels).
- **Côté médecine générale**, des produits que des confrères vous citeront :
  **Nabla** (français, ISO 27001, pas de conservation de l'audio brut, devis sur mesure),
  **Heidi** (50–80 €/mois, 110+ langues, très souple sur les trames),
  **Tandem Health** (69–79 €/mois), **Praxy Santé** (19–59 €/mois, **HDS certifié**,
  serveurs en France), **Markus Santé** (49 €/mois, orienté kiné).

---

## 3. Étranger

### 3.1 Dentaire

| Produit | Pays | Ce qu'il fait | Intégrations | Prix affiché |
|---|---|---|---|---|
| **Bola AI** | US | Référence du dentaire : charting vocal (**Voice Perio**, Voice Restorative) + scribe ambiant. 10 000+ praticiens, 3 M+ dossiers annoncés | **Dentrix (partenariat vérifié), Eaglesoft, Open Dental (bridge)** | non public |
| **Denti.AI** | US | Radio **agréée FDA** + perio vocal + scribe | Dentrix, Eaglesoft, Open Dental + 7 autres | 49–199 $/mois |
| **Kiroku** | UK | **Le plus proche d'Oris** : Co-Pilot écoute et rédige selon *votre* trame ; 50+ trames dentaires, sélecteur de dents, mode « freestyle » sans trame ; Kiroku Docs transforme la note en courriers, lettres au médecin traitant, **formulaires de consentement** | export vers la plupart des logiciels, pas d'écriture native | ~48 $/mois (43 $ à l'année) |
| **DentScribe** | US | Notes SOAP temps réel, publication automatique dans le logiciel | Dentrix, Eaglesoft, Open Dental | non public |
| **VoiceboxMD** | US | Dictée d'abord, écoute ambiante en option ; perio vocal en bêta | **50+ logiciels** | 49 $ / 139 $ (ambiant) |
| **Curve Dental** | US | Écoute ambiante **native dans le logiciel de gestion cloud** | — (c'est le logiciel) | intégré |
| **Overjet / Pearl / VideaHealth** | US | Imagerie : caries, os, 30+ conditions ; **8 agréments FDA pour Pearl**, 3 pour VideaHealth ; Pearl annonce 92 % de sensibilité carie sur 8 700 radios | logiciels de gestion et imagerie | non public |

### 3.2 Médical généraliste (ce sont eux qui fixent le standard de qualité)

- **Abridge** — n°1 KLAS deux années de suite. Sa fonction phare : **Linked Evidence**,
  qui **rattache chaque ligne du compte rendu au passage exact de la transcription et à
  l'horodatage de l'audio**, que le praticien peut réécouter. C'est exactement le
  principe d'Oris (`evidence_segment_ids`), mais **rendu visible au praticien**.
- **Nuance DAX Copilot** (Microsoft) — le poids lourd, très lié à Epic.
- **Nabla**, **Heidi**, **Suki**, **Corti**, **Tandem**, **Freed**, **Scribeberry** —
  autoservice, 39 à 150 $/mois selon les offres.
- Tendance 2026 côté plateformes : codage automatique (ICD-10), **préparation des
  prescriptions et des demandes d'examens**, **résumé de l'historique du patient avant
  la consultation**, écriture en retour dans le dossier (write-back).

---

## 4. Benchmark fonctionnel — Oris face aux autres

Légende : ● présent · ◐ partiel · ○ absent · — sans objet.

| Fonction | **Oris** | Askara | Kiroku | Bola AI | Doctolib | Abridge / Nabla |
|---|---|---|---|---|---|---|
| Écoute de la consultation, sans dictée | ● | ● | ● | ● | ● | ● |
| Dictée / notes vocales | ◐ (corrections vocales web) | ● | ● | ● | ● | ● |
| Compte rendu structuré | ● | ● | ● | ● | ● | ● |
| Plan de traitement | ● | ● | ◐ | ◐ | — | — |
| Courriers confrères | ● | ● | ● | ○ | ● | ● |
| Ordonnances | ○ | ● | ○ | ○ | ◐ | ● |
| Fiches labo, CR de cone beam | ○ | ● | ○ | ○ | ○ | — |
| Consentement éclairé | ○ | ◐ | ● | ○ | ○ | ○ |
| Devis / CCAM / facturation | ○ | ◐ (annoncé) | ○ | ○ | ○ | ◐ (codage) |
| Charting parodontal à la voix | ○ | ○ | ◐ (sélecteur de dents) | ● | ○ | — |
| Numérotation dentaire FDI contrôlée | ● | ? | ◐ | ● | — | — |
| Trames personnalisables par le praticien | ◐ (modèles d'actes) | ◐ | ● (50+, import de la vôtre) | ◐ | ◐ | ● |
| **Preuve : chaque fait cite le passage source** | ● | ? | ? | ? | ? | ● |
| **Cliquer une phrase et voir les paroles sources** | ● (site et iPhone, 26/09/2026) | ? | ? | ? | ? | ● |
| **Réécoute de l'audio au clic sur une phrase** | ○ (son effacé après traitement) | ? | ? | ? | ? | ● |
| Objet clinique unique, documents = projections | ● | ? | ○ | ○ | ? | ◐ |
| Règles déterministes (négation, temporalité, statut) | ● | ? | ○ | ○ | ? | ◐ |
| Refus explicite plutôt que réparation silencieuse | ● | ? | ? | ? | ? | ? |
| Apprentissage tracé des corrections | ● | ◐ | ◐ | ◐ | ◐ | ● |
| **App iPhone native + site, à parité** | ● | ◐ | ◐ | ◐ | ● | ● |
| Photos cliniques dans le document | ● | ○ | ○ | ○ | ○ | ○ |
| **Passerelle SmileCloud** | ● | ○ | ○ | ○ | ○ | ○ |
| Écriture dans le logiciel de gestion | ○ | ◐ | ○ | ● | ● | ● |
| Imagerie / détection de caries | ○ | ○ | ○ | ◐ (Denti.AI) | ○ | ○ |
| Accueil téléphonique | ○ | ○ | ○ | ○ | ● | ○ |
| Hébergement HDS effectif | ○ (à faire) | ● annoncé | ○ | — | ● | ◐ |

### Ce qu'Oris a et que les autres n'annoncent pas

1. **L'objet clinique comme source de vérité.** Chez presque tous les autres, le produit
   fini est *le texte*. Chez Oris, le texte est une projection de faits structurés : une
   correction corrige le fait, puis les documents se refont. C'est ce qui rend la
   cohérence entre compte rendu, plan de traitement et courrier automatique au lieu
   d'être manuelle.
2. **La preuve par segment, imposée au moteur.** Un fait sans segment cité est refusé.
   Abridge a la même idée, personne d'autre ne l'affiche.
3. **Les règles déterministes** (FDI valide, négation préservée, « proposé » ≠
   « accepté » ≠ « réalisé ») qui **rejettent** une sortie non conforme au lieu de la
   rafistoler.
4. **Les photos cliniques et SmileCloud** dans le document : personne d'autre.
5. **Téléphone et ordinateur à parité stricte**, y compris la retouche d'image.

### Ce que les autres ont et pas nous — par ordre de gêne réelle

1. **L'écriture dans le logiciel de gestion** (Julie, Logosw, Desmos…). C'est le point
   n°1, cité par tous les comparatifs comme le différenciateur décisif de Bola AI. Tant
   qu'Oris ne pousse rien dans le dossier patient du cabinet, le praticien fait un
   copier-coller — ou vit avec deux dossiers.
2. **L'ordonnance.** Askara la produit, pas nous. C'est le document dentaire le plus
   fréquent après le compte rendu.
3. **La trame du praticien.** Kiroku laisse importer sa propre trame et la convertit en
   cinq minutes. Oris impose ses modèles d'actes.
4. **La réécoute de l'audio** au clic (Linked Evidence) : impossible chez nous, le son
   est effacé dès la fin du traitement. Le texte de ce qui a été dit, lui, s'affiche
   désormais sur les deux clients.
5. **Le consentement éclairé**, le **devis**, la **fiche labo** : trois documents
   quotidiens que nous ne produisons pas.
6. **L'HDS.** Askara, Doctolib et Praxy l'annoncent. C'est la première question que
   posera un confrère.
7. **Le résumé de l'historique avant la consultation** : tendance 2026 générale, absente
   chez nous.

---

## 5. Prix du marché

| Produit | Prix public |
|---|---|
| Praxy Santé | 19–59 €/mois |
| Kiroku | ~43–48 $/mois |
| Denti.AI | 49–199 $/mois |
| Heidi | 50–80 €/mois |
| Tandem Health | 69–79 €/mois |
| Doctolib Assistant de consultation | 79 €/mois (+ abonnement) |
| **Askara** | **43–129 €/mois** (écoute = 129 €) |
| VoiceboxMD | 49 $ / 139 $ |
| DeepCura | 129 $/mois |

**Fourchette utile pour Oris : 79 à 129 €/mois par praticien**, dégressif à partir du
deuxième praticien du cabinet — c'est la grille Askara, et un confrère comparera
d'abord à elle. En dessous de 79 €, le produit paraîtra léger ; au-dessus de 129 € sans
HDS ni passerelle logiciel métier, il sera refusé.

---

## 6. Le cadre réglementaire, en clair

Trois textes s'appliquent en même temps en 2026 :

- **RGPD** — données de santé, article 9. Rien de nouveau, mais tout s'y rattache.
- **Certification HDS** — les données de santé ne peuvent être hébergées que chez un
  prestataire certifié. **C'est le point dur de la commercialisation d'Oris** ; il est
  déjà acté dans la feuille de route (D027, serveur unique hébergé HDS).
- **AI Act européen** — applicable en 2026. Un logiciel d'aide au **diagnostic** est
  classé « haut risque », avec gestion des risques sur tout le cycle de vie, qualité des
  données d'entraînement et contrôle humain effectif.
- **MDR (dispositif médical)** — un logiciel « destiné à poser un diagnostic, orienter un
  traitement ou trier des patients » doit porter le **marquage CE**. Allisone l'a.

**Conséquence pour Oris, et c'est une bonne nouvelle :** tant qu'Oris **documente ce qui
a été dit** sans poser de diagnostic ni recommander de traitement, il reste hors du
champ du dispositif médical. Les quatre promesses de `POSITIONNEMENT.md` (« n'invente
aucun fait », « ne valide rien seul », « ne pose pas de diagnostic », « apprend le style,
jamais le contenu ») ne sont pas seulement une ligne éthique : **ce sont elles qui
gardent Oris hors du marquage CE**. Le jour où Oris suggérerait un diagnostic, le coût
réglementaire changerait d'ordre de grandeur.

---

## 7. Ce que je recommande

Par ordre de rapport valeur / effort.

**À faire d'abord (petit effort, effet immédiat sur la démonstration)**

1. ~~**Rendre la preuve visible**~~ — **fait le 26/09/2026** : le site l'avait déjà dans
   son rail de révision ; l'iPhone l'a maintenant aussi, et les deux lisent la même
   route. Reste à le *dire* : c'est l'argument qu'aucun concurrent français n'affiche,
   il doit figurer sur la plaquette et dans la démonstration.
2. **L'ordonnance** comme nouveau type de document, avec les mêmes garde-fous.
3. **Le consentement éclairé** généré depuis le plan de traitement.

**Ensuite (effort moyen, lève une objection de vente)**

4. **Trames du praticien** : importer sa propre structure de compte rendu.
5. **Résumé d'avant-consultation** : ce qui a été fait la dernière fois, ce qui reste au
   plan de traitement.
6. **Export propre vers le logiciel métier** : à défaut d'API, un bloc texte formaté et
   copiable en un clic, plus le PDF. Étudier la passerelle Julie/Logosw/Desmos.

**Enfin (structurant)**

7. **HDS** — déjà dans la feuille de route commercialisation, en attente.
8. **Devis / CCAM** depuis le plan de traitement : c'est là qu'Askara va aller.

**À ne pas faire :** l'imagerie (Allisone, Pearl, Overjet ont dix ans d'avance et des
agréments), le standard téléphonique (DentalCall, Doctolib), le logiciel de gestion.
Oris doit rester le meilleur sur *une* chose : transformer une consultation parlée en
documentation juste et traçable.

---

## Sources

France — dentaire
- [Askara — site produit](https://www.askara.ai/en) · [tarifs](https://www.askara.ai/en/pricing) · [compte rendu patient](https://www.askara.ai/en/documents/patient-letter)
- [Askara : avis, prix et alternatives (rcpt.ai)](https://rcpt.ai/blog/askara)
- [Askara s'ouvre aux orthodontistes (Dentaire365)](https://www.dentaire365.fr/praticien/orthodontiste-praticien/askara-plateforme-dintelligence-artificielle-souvre-aux-orthodontistes/)
- [Askara — Initiatives Nouvelles](https://www.initiatives-nouvelles.com/askara-lia-qui-libere-les-chirurgiens-dentistes-de-la-paperasse/)
- [Les acteurs IA du cabinet dentaire (DentalCall)](https://www.dentalcall.ai/ressources/quels-sont-les-differents-acteurs-ia-qui-transforment-le-quotidien-des-cabinets-dentaires)
- [Comparatif logiciel dentaire 2026 (DentalIAssist)](https://dentaliassist.fr/blog/comparatif-logiciel-dentaire-2026)
- [IA dentaire au quotidien (rcpt.ai)](https://rcpt.ai/blog/ia-dentaire-transforme-quotidien-cabinets)
- [Allisone lève 10 M€ (L'Usine Digitale)](https://www.usine-digitale.fr/article/la-start-up-allisone-leve-10-millions-d-euros-pour-digitaliser-les-soins-dentaires-grace-a-l-ia.N2039152)
- [Allisone — Dentaire365](https://www.dentaire365.fr/exposant/allisone/) · [Health Data Hub](https://www.health-data-hub.fr/projets/evaluation-dun-dispositif-medical-allisone-ai-destine-faciliter-lidentification-de-0)

France — médical
- [Doctolib — Assistant de consultation](https://www.doctolib.fr/sante/assistant-consultation/)
- [Doctolib étend son assistant téléphonique aux dentistes (L'Usine Digitale)](https://www.usine-digitale.fr/sante/doctolib-renforce-son-offre-ia-avec-un-assistant-telephonique-pour-les-generalistes-et-les-chirurgiens-dentistes.PQVTIGZCWVDJBG4JT2QDOLQP7Q.html)
- [Comparatif transcription médicale 2026 (Markus Santé)](https://www.markus-sante.com/blog/transcription-medicale-nabla-heidi-doctolib-tandem-praxy)
- [Nabla veut imposer son IA médicale en France (Cafétech)](https://cafetech.fr/2025/12/05/apres-les-etats-unis-nabla-veut-imposer-son-ia-medicale-en-france/)

Étranger
- [Best AI Scribe for Dentists 2026 — 9 outils comparés (DeepCura)](https://www.deepcura.com/resources/best-ai-scribe-for-dentists)
- [Kiroku](https://www.trykiroku.com/) · [Kiroku AI](https://www.trykiroku.com/ai)
- [Bola AI — Voice Perio](https://bola.ai/solutions/voice-perio/) · [Bola × Dentrix](https://bola.ai/practice-management-partners/dentrix/) · [Open Dental](https://www.opendental.com/site/bolaai.html)
- [Abridge — Verify a Note With Linked Evidence](https://support.abridge.com/hc/en-us/articles/30235128433811-Verify-a-Note-With-Linked-Evidence)
- [Pearl vs Videa vs Overjet en 2026 (Becker's Dental Review)](https://www.beckersdental.com/ai-teledentistry/pearl-vs-videa-vs-overjet-what-3-ai-giants-have-accomplished-in-2026/)
- [Dental AI FDA Clearance Tracker](https://aidentaltools.com/clinical-ai/dental-ai-fda-clearance-tracker/)
- [The Ambient Dental Practice (Curve Dental)](https://www.curvedental.com/blog/the-ambient-dental-practice)
- [Comparatif AI scribes 2026 (iatroX)](https://www.iatrox.com/academy/toolkits/ai-scribe-comparison-2026)

Réglementaire
- [IA dans la santé et HDS 2026](https://ayinedjimi-consultants.fr/articles/ia-sante-hds-conformite-2026)
- [IA et données de santé : RGPD, HDS et AI Act](https://vocalyse.ai/blog/ia-donnees-de-sante-rgpd-hds-reglement-ia)
- [Ce que MDR, HDS et RGPD imposent (Playmoweb)](https://playmoweb.com/application-sante-connectee-mdr-hds-rgpd)
