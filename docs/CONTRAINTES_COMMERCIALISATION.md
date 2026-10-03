# Commercialiser Oris — toutes les contraintes

*Écrit le 4 octobre 2026, à la demande de Franck. Complète
`docs/FEUILLE_DE_ROUTE_COMMERCIALISATION.md` (le « comment »), qui reste en attente :
ce fichier-ci dit le « ce qu'il faut respecter ».*

> **Ce document n'est pas un avis juridique.** Il rassemble ce que disent les textes et
> les sources publiques à cette date, pour que vous sachiez quoi demander à qui. Trois
> points au moins devront être tranchés par écrit par un spécialiste : le statut de
> dispositif médical, le partage de responsabilité HDS, et les contrats de sous-traitance.
> Les règles de 2026 bougent vite (AI Act, transferts vers les États-Unis) : à revérifier
> avant toute signature.

---

## 0. En une page

Vendre Oris, ce n'est pas vendre un logiciel : c'est **prendre en charge les données de
santé des patients d'autrui**. Tout découle de là.

Cinq obligations commandent le reste :

| # | Obligation | Pourquoi c'est bloquant |
|---|---|---|
| 1 | **Hébergement HDS** | On ne peut pas héberger des données de santé pour le compte d'un tiers hors d'un hébergeur certifié |
| 2 | **Contrat de sous-traitance RGPD** avec chaque cabinet client | Sans lui, le cabinet est en faute et vous aussi |
| 3 | **Messagerie sécurisée de santé (MSSanté)** | Le courriel ordinaire est interdit pour transmettre des données de santé depuis 2021 — **Oris l'utilise aujourd'hui** |
| 4 | **Ne pas devenir un dispositif médical** | Dès qu'Oris « aide au diagnostic », il faut un marquage CE : des années et un budget d'un autre ordre |
| 5 | **Vraie authentification** (compte, mot de passe, second facteur, idéalement e-CPS) | Un jeton collé à la main ne tient pas une minute devant un auditeur |

Le reste — AI Act, Ségur, INS, assurance, société — s'organise autour.

---

## 1. Qui est responsable de quoi (la question qui commande tout)

Au sens du RGPD :

- **Le cabinet client est « responsable de traitement »** : c'est lui qui décide de
  soigner, de documenter, de garder. Les données sont les siennes.
- **Vous, éditeur d'Oris, seriez « sous-traitant »** : vous traitez ces données *pour son
  compte*, selon ses instructions.
- **Deepgram, Anthropic, l'hébergeur** seraient vos **sous-traitants ultérieurs**.

Conséquences concrètes :

1. Un **contrat de sous-traitance (article 28 RGPD)** doit être signé avec chaque cabinet.
   Il dit ce que vous faites des données, où elles sont, qui y accède, combien de temps,
   ce qui se passe à la fin.
2. Le cabinet doit **autoriser par écrit** vos sous-traitants ultérieurs, et être prévenu
   de tout changement (si vous changez de moteur de transcription, il doit pouvoir s'y
   opposer).
3. Vous ne pouvez **rien faire des données pour votre compte** — pas d'entraînement de
   modèle, pas de statistiques commerciales — sans base légale distincte et accord
   explicite. C'est un point sur lequel les confrères vous interrogeront.
4. En cas de fuite, **c'est le cabinet qui notifie la CNIL** sous 72 h, mais c'est vous
   qui devez le prévenir « dans les meilleurs délais » et lui fournir tout ce qu'il faut.

---

## 2. L'hébergement : la certification HDS

### Ce que dit la règle

Héberger des données de santé **pour le compte d'un tiers** impose un hébergeur certifié
HDS (article L. 1111-8 du code de la santé publique). Le référentiel compte **six
activités** ; les deux dernières sont celles qui piègent les éditeurs :

| Activité | De quoi il s'agit |
|---|---|
| 1 et 2 | Mise à disposition et maintien des sites physiques et du matériel |
| 3 et 4 | Infrastructure virtuelle, plateforme logicielle |
| **5** | **Administration et exploitation du système d'information** |
| **6** | **Sauvegarde externalisée** |

### Les deux montages possibles

**A. Vous vous appuyez sur un hébergeur certifié (le plus simple).**
Scaleway, OVHcloud, Outscale, Azure, AWS sont certifiés. Scaleway l'est notamment sur ses
*Instances*, en France — c'est la machine que vous avez déjà pour le portail. Il faut
alors un **contrat ou avenant HDS** signé avec lui : la certification de l'hébergeur ne
vous couvre pas toute seule, elle doit être contractualisée pour votre usage.

**B. Vous exploitez vous-même le serveur pour vos clients (l'infogérance).**
Dès que vous installez, surveillez, sauvegardez et dépannez Oris pour le compte d'un
cabinet, vous faites de l'infogérance : **vous devez alors être certifié HDS vous-même
sur les activités 5 et 6**, en plus de votre hébergeur. C'est le cas de figure normal
d'un éditeur SaaS — et c'est le point que seul un spécialiste peut trancher pour votre
montage exact.

### Ordres de grandeur, à confirmer par devis

- Audit et certification HDS d'une petite structure : **plusieurs dizaines de milliers
  d'euros** la première fois, plus un audit de surveillance annuel, et des mois de
  préparation (système de management de la sécurité, procédures, preuves).
- Hébergement lui-même : quelques centaines d'euros par mois pour commencer.

### À savoir pour 2026

Le référentiel a changé (HDS v2) : les acteurs devaient y être passés **avant le 16 mai
2026**. Toute offre que vous regarderez doit être à jour de cette version.

---

## 3. Les fournisseurs d'IA : le point le plus fragile

Aujourd'hui, Oris envoie **le son à Deepgram** et **le texte à Anthropic**, aux
États-Unis. Pour votre usage personnel c'est votre affaire ; pour des clients, ça devient
le maillon faible.

- Un transfert hors de l'Union doit s'appuyer sur un mécanisme valide. Le **EU-US Data
  Privacy Framework** reste en vigueur, mais une décision de la Cour suprême américaine
  du **29 juin 2026** le fragilise sérieusement. Construire un produit vendu sur ce seul
  socle est imprudent.
- Les **clauses contractuelles types** restent l'outil de repli, mais elles imposent une
  analyse des risques (le fameux « transfer impact assessment ») et des mesures
  complémentaires.
- **La solution propre, et celle que vos confrères comprendront : rester en Europe.**
  Claude est servi depuis des régions européennes via AWS Bedrock ou Google Vertex ;
  Azure AI Speech transcrit en France ; des moteurs de transcription peuvent être
  auto-hébergés. C'est un travail d'intégration, pas une révolution — les interfaces
  fournisseurs d'Oris ont justement été faites pour ça.
- Dans tous les cas : **contrat de sous-traitance signé avec chacun**, interdiction
  d'entraîner sur vos données, durée de conservation nulle ou documentée.

Le mémo `docs/VENDORS.md` liste déjà ce qui sort d'Oris. Ses colonnes « à documenter »
sont exactement ce que ces contrats doivent remplir.

---

## 4. RGPD : le détail de ce qu'il faut tenir

**Base légale.** Côté cabinet, le traitement repose sur la prise en charge du patient
(article 9.2.h du RGPD) — pas sur le consentement, qui serait fragile. L'enregistrement
de la consultation, lui, demande une attention particulière : ce n'est pas un acte de
soin ordinaire.

**Information du patient.** Elle est obligatoire et doit être **loyale, préalable et
compréhensible** : que la consultation est écoutée, par quel outil, pour quoi faire,
combien de temps le son est gardé (chez Oris : effacé dès la transcription faite), qui y
a accès, et comment s'y opposer. En pratique : une affiche en salle d'attente, une
mention dans le livret d'accueil, et une phrase dite au fauteuil. Oris devra **fournir ces
modèles à ses clients** — c'est un argument de vente autant qu'une obligation.

**Droit d'opposition.** Un patient doit pouvoir refuser l'écoute sans que son soin en
pâtisse. Donc : un bouton « ne pas écouter cette consultation », et la trace de ce refus.

**Analyse d'impact (AIPD).** Pour un traitement de données de santé à cette échelle, avec
de l'IA et des sous-traitants hors UE, elle est **à considérer comme obligatoire**. Elle
se prépare une fois et se met à jour ; c'est un document que vos clients vous demanderont.

**Registre des traitements**, côté éditeur comme côté cabinet.

**Délégué à la protection des données (DPO).** Non obligatoire par principe pour une
petite structure, mais le traitement « à grande échelle » de données de santé y mène
vite. À prévoir, au moins en externe et à temps partagé.

**Durées de conservation.** Le dossier d'un patient se garde longtemps (la référence
usuelle est de **20 ans** après le dernier acte). Oris doit donc : conserver ce qu'il
faut, purger le reste (le son l'est déjà), et surtout **rendre les données** au cabinet.

**Réversibilité.** Un client qui part doit repartir avec tout, dans un format lisible,
et vous devez effacer ensuite, avec un procès-verbal. À écrire dans le contrat **et** à
construire dans le produit.

**Violation de données.** Procédure écrite, délai de 72 h côté cabinet, donc alerte
immédiate de votre part. À tester une fois à blanc.

---

## 5. Secret médical et transmission : le point dur d'aujourd'hui

L'article L. 1110-4 du code de la santé publique impose l'échange **sécurisé** des données
de santé. Depuis le 1er janvier 2021, **le courriel ordinaire est interdit** pour
transmettre des données de santé identifiantes entre professionnels. Les sanctions sont
administratives, ordinales, voire pénales.

**Or Oris envoie aujourd'hui ses documents par Gmail (SMTP).** C'est acceptable pour vos
essais ; c'est rédhibitoire pour un produit vendu.

Ce qu'il faut :

- l'envoi aux **confrères** via **MSSanté** (l'adresse professionnelle sécurisée, celle
  en `@medecin.mssante.fr` et équivalents) ;
- l'envoi **au patient** via « Mon espace santé » ou un canal sécurisé équivalent ;
- à défaut, un lien de téléchargement protégé — mais MSSanté est ce que les confrères
  attendent, et ce que le Ségur finance.

C'est un chantier technique identifié, pas une impasse.

---

## 6. Dispositif médical : la ligne à ne pas franchir

Un logiciel devient dispositif médical **par sa destination revendiquée** : s'il sert à
diagnostiquer, orienter un traitement ou trier des patients, il relève du règlement
européen 2017/745, doit porter le **marquage CE**, et la règle 11 le classe en général en
IIa au minimum — avec organisme notifié, système qualité ISO 13485, documentation
technique, surveillance après commercialisation. Comptez des années et un budget sans
rapport avec le reste de cette page.

**Oris documente ce qui a été dit. Il ne diagnostique pas.** Tant que c'est vrai, il reste
hors du champ. Mais « tant que c'est vrai » engage :

- **le produit** : pas de suggestion de diagnostic, pas de proposition de traitement, pas
  de score de risque, pas d'alerte clinique ;
- **le discours commercial** : une plaquette qui promet « une aide au diagnostic » suffit
  à faire basculer la qualification, même si le logiciel ne le fait pas. Les quatre
  promesses de `docs/POSITIONNEMENT.md` sont, de ce point de vue, un actif juridique ;
- **les régulateurs regardent ce sujet** : l'agence britannique a publié en 2026 une
  doctrine sur les scribes IA, distinguant la documentation administrative (hors champ)
  des outils qui produisent des « insights » cliniques (dans le champ).

**À faire :** obtenir un **avis écrit** de qualification avant toute vente, et le garder.
C'est peu coûteux et ça vous protège.

---

## 7. AI Act européen

Le calendrier a bougé en 2026, il faut le connaître :

- **2 août 2026** : application générale, et surtout les **obligations de transparence de
  l'article 50** — l'utilisateur doit savoir qu'il a affaire à une IA, et les contenus
  générés doivent être identifiables comme tels. Les systèmes déjà sur le marché avaient
  jusqu'au **2 décembre 2026** pour s'y conformer.
- Le « Digital Omnibus » adopté en juin 2026 a **repoussé au 2 décembre 2027** les
  obligations lourdes des systèmes à haut risque de l'annexe III.
- Un logiciel est « haut risque » notamment lorsqu'il est **dispositif médical soumis à
  évaluation par un organisme notifié**. Autrement dit : **si Oris reste hors du champ du
  dispositif médical, il n'est pas haut risque** — ce qui est une raison de plus de tenir
  la ligne du §6.

Ce qui s'applique donc à Oris : la **transparence** (dire que c'est une IA, que le
document est un brouillon à valider), la **documentation** de ce que fait le système, et
la **supervision humaine** — toutes choses déjà dans l'architecture. Il faudra les écrire
proprement dans un document destiné aux clients.

---

## 8. Le guide HAS / CNIL « IA en contexte de soins »

Publié en **février 2026** après consultation publique, c'est la référence française du
moment. Il est organisé en **dix fiches** couvrant tout le cycle de vie d'un système d'IA
(de l'achat à la désinstallation), plus deux fiches sur la gouvernance et l'IA générative,
et classe ses conseils en quatre niveaux : **obligations légales**, recommandations
standard, recommandations avancées, réflexes à adopter.

Deux usages pour vous :

1. **comme grille d'auto-contrôle** avant de vendre ;
2. **comme argument** : un confrère ou un groupe qui vous challenge sera rassuré de voir
   qu'Oris a été passé au crible de ce guide. C'est un travail que je peux faire, fiche
   par fiche.

---

## 9. Ségur du numérique, INS et DMP

Le **Ségur vague 2 inclut désormais les chirurgiens-dentistes** (documents publiés le
3 mars 2026 ; développements attendus des éditeurs en 2026-2027). Un logiciel référencé
doit notamment :

- utiliser l'**INS** (identité nationale de santé) pour identifier le patient de façon
  fiable — ce qui impose les règles d'identitovigilance et un appel au téléservice INSi ;
- **alimenter le DMP** (« Mon espace santé ») avec les documents produits ;
- **utiliser MSSanté** pour les échanges (voir §5).

Ce n'est pas obligatoire au sens strict, mais c'est **ce qui ouvre les financements** et
ce que les confrères auront pris l'habitude d'exiger. Pour Oris, c'est une décision
stratégique : viser le référencement (travail conséquent, crédibilité et financement) ou
rester un outil « à côté » du logiciel de gestion (plus simple, moins défendable face à
Askara qui ira probablement s'y brancher).

---

## 10. Le produit lui-même : ce qu'un audit regardera

Rien d'exotique, mais rien d'optionnel :

- **comptes et connexion** : fini le jeton collé à la main. Mail + mot de passe + second
  facteur, et à terme **Pro Santé Connect / carte e-CPS**, que les praticiens connaissent ;
- **rôles** : praticien, assistante, administrateur du cabinet, et cloisonnement strict
  entre cabinets (déjà en place dans le modèle de données) ;
- **journal d'audit** inaltérable : qui a vu quoi, quand (déjà en place) ;
- **chiffrement** en transit et au repos, gestion des clés ;
- **sauvegardes chiffrées et restauration réellement essayée** — une sauvegarde non
  testée ne compte pas ;
- **supervision, journaux sans donnée patient** (déjà la règle dans le code) ;
- **plan de reprise** : que se passe-t-il si le serveur brûle, et en combien de temps ;
- **test d'intrusion** par un tiers avant mise en service ;
- **deux environnements** séparés : essai avec données fictives, production ;
- **procédure de départ d'un client** (export + effacement + preuve).

---

## 11. L'entreprise

- **Structure juridique** (SASU ou SAS) : nécessaire pour facturer, signer avec un
  hébergeur, contracter avec des cabinets. Tant que vous vendez en nom propre, votre
  patrimoine est exposé.
- **Assurance responsabilité civile professionnelle** couvrant explicitement l'édition de
  logiciel de santé et le risque cyber. À négocier avant la première vente.
- **CGU / CGV**, contrat de licence, contrat de sous-traitance RGPD, engagement de niveau
  de service (disponibilité, délai de rétablissement, support).
- **Propriété intellectuelle** : le code vous appartient ; pensez au dépôt des marques
  « Oris » et du logo (vérifier d'abord la disponibilité à l'INPI — « Oris » est aussi une
  marque d'horlogerie, ce qui n'est pas forcément bloquant dans votre classe, mais c'est à
  vérifier).
- **Compte développeur Apple « organisation »** (numéro D-U-N-S) pour publier l'app au nom
  de la société, plus la conformité App Store des apps de santé.
- **Comptabilité, TVA**, et le cas particulier des éventuelles subventions Ségur.

---

## 12. Ce qui, chez Oris aujourd'hui, empêche la vente

La liste honnête, au 4 octobre 2026 :

| Point | État | Gravité |
|---|---|---|
| Envoi des documents par Gmail | À remplacer par MSSanté | **Bloquant** |
| Accès par jeton collé à la main | À remplacer par de vrais comptes | **Bloquant** |
| Données sur le Mac du cabinet | À déplacer chez un hébergeur HDS | **Bloquant** |
| Transcription et rédaction aux États-Unis | À basculer en Europe | **Bloquant** |
| Clés d'API dans un fichier `.env` | À passer en gestion de secrets | Élevée |
| Pas d'INS ni de DMP | Décision stratégique (§9) | Moyenne |
| Pas de sauvegardes ni de restauration essayée | À construire | Élevée |
| Pas de mention d'information patient fournie | À écrire et à livrer aux clients | Élevée |
| Pas d'avis écrit sur le statut de dispositif médical | À obtenir | Élevée |
| Pas de structure juridique ni d'assurance | À créer avant la première vente | **Bloquant** |

Rien, dans cette liste, n'est un mur technique. Ce sont des mois de travail et quelques
milliers d'euros de conseils — plus le coût de l'hébergement conforme.

---

## 13. L'ordre de marche que je recommande

1. **Faire trancher le statut de dispositif médical** par un spécialiste (quelques
   centaines d'euros, protège tout le reste).
2. **Décider du montage d'hébergement** : hébergeur certifié + avenant HDS, ou
   certification propre. Demander deux devis. C'est ce qui dimensionne le projet.
3. **Basculer l'IA en Europe** (Claude via Bedrock/Vertex UE, transcription Azure France)
   et signer les contrats de sous-traitance. Travail que je peux faire.
4. **Comptes, connexion, MSSanté, sauvegardes** : les quatre chantiers produit. Travail
   que je peux faire.
5. **Écrire les documents** : AIPD, registre, contrat de sous-traitance type, mention
   d'information patient, documentation AI Act, grille HAS/CNIL. Je peux préparer les
   brouillons ; un juriste les relit.
6. **Créer la société et assurer**.
7. **Pilote** avec deux ou trois cabinets amis, sous contrat, avec données réelles — et
   seulement après les étapes 1 à 6.

---

## Sources

Hébergement et données de santé
- [Certification HDS 2026 : référentiel v2, démarche, coûts (Legiscope)](https://www.legiscope.com/blog/hebergement-hds-certification.html)
- [Hébergement HDS : guide pour éditeurs et professionnels de santé (Nubevia)](https://nubevia.com/blog/hebergement-hds-comment-heberger-ses-donnees-de-sante-en-2026/)
- [Certification HDS v2 : ce qui change en 2026 (Ad'valorem)](https://www.advalorem.fr/certification-hds-v2-2026/)
- [Scaleway — hébergement des données de santé et certification HDS](https://www.scaleway.com/en/security-and-compliance/hds/)
- [Fiche hébergeur HDS — Scaleway](https://www.hebergeurs-de-donnees-de-sante.fr/hebergeurs/scaleway/)

Transferts hors UE
- [EU-US Data Privacy Framework under pressure (Thryve Health)](https://www.thryve.health/blog/eu-us-dpf-supreme-court-health-data)
- [FAQ du Comité européen de la protection des données sur le DPF (janvier 2026)](https://www.edpb.europa.eu/system/files/2026-01/edpb_dpf_faq-for-individuals_v2_en.pdf)

Secret médical et messagerie
- [Repères juridiques MSSanté (Mailiz)](https://mailiz.mssante.fr/reperes-juridiques)
- [Envoyer un dossier patient par mail : est-ce autorisé ? (Komper)](https://www.komper.fr/blog/envoyer-dossier-patient-mail)

Dispositif médical
- [Logiciels médicaux intégrant de l'IA : règles et classifications (Sparta)](https://sparta.care/post/logiciels-medicaux-integrant-de-lia-quelles-sont-les-regles-et-classifications-a-connaitre-34fa3)
- [Bases du marquage CE pour un fabricant de DM numérique (Sparta)](https://www.sparta.care/post/les-bases-du-marquage-ce-pour-un-fabricant-de-dispositif-medical-numerique-c7e21)
- [MHRA — quand un scribe IA est un dispositif médical (2026)](https://meddeviceguide.com/blog/mhra-ambient-voice-technology-avt-ai-scribe-medical-device-qualification-guide)

AI Act
- [EU AI Act deadlines 2026-2027 (Legiscope)](https://www.legiscope.com/blog/eu-ai-act-timeline-deadlines.html)
- [AI Act : ce qui change le 2 août 2026 (AI Acto)](https://www.aiacto.eu/en/blog/ai-act-what-changes-august-2-2026)
- [High-level summary of the AI Act](https://artificialintelligenceact.eu/high-level-summary/)

France — IA en santé
- [Guide HAS/CNIL « IA en contexte de soins », février 2026 (AP-HP)](https://affairesjuridiques.aphp.fr/textes/guide-has-cnil-accompagner-le-bon-usage-des-systemes-dintelligence-artificielle-en-contexte-de-soins-fevrier-2026/)
- [HAS et CNIL lancent la consultation publique (mind Health)](https://www.mind.eu.com/health/article/la-has-et-la-cnil-lancent-une-consultation-publique-sur-le-guide-ia-en-contexte-de-soins/)
- [Référentiels CNIL pour le secteur de la santé](https://www.cnil.fr/fr/la-cnil-publie-trois-referentiels-pour-le-secteur-de-la-sante)

Ségur, INS, DMP
- [Ségur du numérique en santé — vague 2 (ANS)](https://esante.gouv.fr/ens/segur-numerique-sante/vague-2)
- [Ségur du numérique en santé — espace éditeurs (ANS)](https://esante.gouv.fr/ens/segur-numerique-sante)
