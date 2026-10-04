# Oris au crible du guide HAS / CNIL

*Audit mené le 4 octobre 2026 contre le guide **« Accompagner le bon usage des systèmes
d'intelligence artificielle en contexte de soins »**, HAS et CNIL, février 2026 —
61 pages, 12 chapitres, 48 recommandations.*

> Ce n'est pas un avis juridique. C'est une lecture du guide, recommandation par
> recommandation, confrontée à ce que fait réellement le code d'Oris aujourd'hui.

---

## 1. Comment lire ce guide quand on est Franck

Le guide s'adresse au **déployeur** — l'établissement ou le praticien libéral qui décide
d'utiliser une IA — et non au fournisseur. Vous êtes donc concerné **deux fois** :

- **aujourd'hui, comme déployeur** : vous utilisez Oris sur vos propres patients. Les
  obligations du guide s'appliquent déjà à vous ;
- **demain, comme fournisseur** : chaque recommandation adressée au déployeur se traduit
  en **quelque chose qu'Oris devra lui fournir**. Le chapitre 2, en particulier, est la
  liste de courses qu'un acheteur vous présentera.

Le guide rappelle une phrase qui mérite d'être lue deux fois :

> « Le professionnel de santé reste entièrement responsable, même lorsque l'acte est
> accompli avec l'assistance d'un SIA. »

---

## 2. La bonne nouvelle d'abord : le classement d'Oris

Le guide tranche explicitement le cas des outils comme le nôtre, en annexe 1 :

> « C'est notamment le cas des SIA utilisés comme **aide à la rédaction de comptes rendus
> médicaux à partir d'une consultation**, considérés à l'heure actuelle comme **SIA à
> risque limité**. »

Et au chapitre 12 :

> « La plupart de ces SIA ne relèvent pas à l'heure actuelle de la définition d'un
> dispositif médical. »

**Autrement dit : Oris est, noir sur blanc, dans la catégorie « risque limité » de l'AI
Act, et hors du champ du dispositif médical.** Pas de marquage CE, pas d'obligations
« haut risque ». Ce qui s'applique, c'est la **transparence** — et c'est précisément là
qu'Oris pèche aujourd'hui (§4.7).

Le guide prévient toutefois : le cadre peut évoluer, comme au Royaume-Uni, où le
régulateur a publié en 2025 une doctrine spécifique aux scribes IA. À surveiller.

---

## 3. Verdict d'ensemble

| # | Chapitre du guide | Où en est Oris |
|---|---|---|
| 1 | Organisation interne et gouvernance | ⚪ Hors périmètre produit — à faire côté cabinet |
| 2 | **Acquisition et contractualisation** | 🔴 **Rien de prêt** : c'est le gros morceau |
| 3 | Vérification de l'adéquation au contexte local | 🟠 Banc d'essai existant, jamais rejoué chez un client |
| 4 | Formation et acculturation | 🔴 Aucun support de formation |
| 5 | Organisation des soins | ⚪ Côté cabinet |
| 6 | Au cours de l'utilisation | 🟠 Bonnes bases, notice d'usage à écrire |
| 7 | **Information des personnes et consentement** | 🔴 **Deux manques nets** (mention IA, consentement voix) |
| 8 | Décision automatisée et contrôle humain | 🟢 **Conforme, et c'est le point fort d'Oris** |
| 9 | Traçabilité des usages | 🟢 Très bon, deux compléments |
| 10 | Vigilance, maintenance, performances | 🟠 Outils présents, routine absente |
| 11 | Fin de cycle de vie et désinstallation | 🔴 Pas d'export client |
| 12 | Spécificités de l'IA générative | 🟢 Conforme sur le fond |

🟢 conforme · 🟠 partiel · 🔴 manquant · ⚪ hors périmètre du produit

---

## 4. Le détail, chapitre par chapitre

### 4.1. Gouvernance (reco 1.1 à 1.8)

Le guide demande une gouvernance de l'IA dans la structure, une **cartographie des SIA
utilisés**, un guichet unique, une validation institutionnelle.

**Pour un cabinet libéral, cela se réduit à peu** : savoir quels outils d'IA sont
utilisés, pour quoi, et l'avoir écrit. Une page suffit.

**À faire (vous, aujourd'hui) :** une page listant Oris (et les autres outils IA du
cabinet), leur finalité, les données traitées. Je peux la rédiger.

### 4.2. Acquisition et contractualisation (reco 2.1 à 2.8) — le gros morceau

La recommandation 2.1 énumère ce que **le contrat doit contenir, fourni par le
fournisseur**. C'est votre future liste de courses :

| Ce que le guide exige | État chez Oris |
|---|---|
| Finalité et destination d'usage | ✅ `docs/POSITIONNEMENT.md` |
| Statut réglementaire (DM ou non, classe) | ❌ À formaliser (et à faire confirmer) |
| Principes algorithmiques, origine des données d'entraînement | 🟠 Oris n'entraîne pas de modèle ; à écrire clairement |
| Modalités d'évaluation, gestion des biais, stratégies d'atténuation | 🟠 Banc d'essai existant, pas de document sur les biais |
| **Performances mesurées** (sensibilité, robustesse…) et contexte de validation | 🟠 Mesures existantes (WER, rôles, extraction) jamais mises en forme |
| **Limites et biais connus** | 🟠 `docs/KNOWN_LIMITATIONS.md` existe, à transformer en document client |
| Populations éligibles, populations non validées | ❌ Rien (ex. : enfants ? patients non francophones ?) |
| Principe de fonctionnement compréhensible, anti « boîte noire » | ✅ C'est le point fort d'Oris |
| **Dispositions minimales de contrôle humain** à mettre en œuvre | 🟠 Pratiqué, jamais écrit |
| Accompagnement à la formation des utilisateurs | ❌ Rien |
| Éléments nécessaires au fonctionnement, fonctionnement dégradé | 🟠 Partiel |
| Procédures en cas d'incident ou de violation de données | ❌ Rien |
| **Flux de données et moteurs tiers (API)** | ✅ `docs/VENDORS.md` — mais à compléter |
| Impact environnemental | ❌ Rien |

S'y ajoutent : **SLA** (reco 2.4), **période de calibrage avec rétractation** (2.5),
**clause de performance** (2.6), **conditions de fin de contrat et réversibilité** (2.7),
**association du DPO** (2.8).

**Conclusion :** Oris possède la matière (positionnement, limites connues, vendeurs,
bancs d'essai) mais **aucun document destiné à un client**. C'est un travail de rédaction,
pas de développement — et c'est ce qui vous sera demandé en premier.

### 4.3. Adéquation au contexte local (reco 3.1 à 3.3)

Le guide demande de vérifier que l'outil convient **au contexte réel** du cabinet, puis de
faire un bilan du déploiement.

Oris a ce qu'il faut (corpus de 100 consultations, banc STT, cas de non-régression), mais
cela mesure Oris **chez vous**. Chez un client, il faudrait rejouer une vérification.

**À prévoir :** un « protocole de calibrage » d'un mois, reproductible, livré avec Oris.

### 4.4. Formation (reco 4.1 à 4.10) — rien

Le guide est exigeant : formation préalable obligatoire, habilitation, contenu
pédagogique, régularité, **traçabilité de la formation**. Pour un cabinet de quelques
personnes, cela reste modeste — mais il faut un support.

**À faire :** une notice d'utilisation (10 pages), une vidéo courte, une fiche
« ce qu'Oris ne sait pas faire ». Aucun n'existe aujourd'hui.

### 4.5. Organisation des soins (reco 5.1 à 5.3)

Rôles et responsabilités des utilisateurs, référent par service, encadrement des
délégations. Côté cabinet. Oris gère déjà des rôles techniques (praticien, cabinet) ; il
faudra les faire correspondre à des rôles réels (assistante, remplaçant).

### 4.6. Au cours de l'utilisation (reco 6.1 à 6.3)

Trois points, et le troisième vise **explicitement** les outils comme Oris :

- **6.1 — Assurance RC professionnelle** : vérifier auprès de votre assureur que l'usage
  d'une IA est couvert. **C'est à faire tout de suite, c'est gratuit, et personne n'y
  pense.**
- **6.2 — Utilisation conforme à la notice** : il faut donc une notice. Et le guide
  avertit qu'un usage non conforme expose le déployeur à **être requalifié en
  fournisseur**, avec toutes les obligations qui vont avec.
- **6.3 — Bonnes pratiques** : le guide cite nommément « les SIA d'aide à la rédaction de
  comptes rendus dont l'utilisation peut nécessiter **d'oraliser une partie de l'examen
  clinique** afin que le système capture les informations pertinentes ». C'est exactement
  la façon dont Oris doit être utilisé, et cela doit figurer dans sa notice.

### 4.7. Information des personnes et consentement (reco 7.1 à 7.4) — deux manques nets

**Manque n° 1 — la mention d'IA dans les documents.** La recommandation 7.3 est explicite
pour les outils d'aide à la rédaction : une information spécifique doit être portée **dans
le compte rendu lui-même**. Le guide donne jusqu'au modèle de phrase :

> « Ce [compte rendu] a été établi(e) avec l'assistance du système d'intelligence
> artificielle [Nom, Version], validé par le Dr [Nom, fonction]. »

**Oris ne l'écrit nulle part.** Ni dans le PDF, ni dans le texte exporté, ni dans le
courrier au confrère — alors que le guide insiste justement sur le cas des échanges entre
professionnels. C'est un petit travail et c'est la correction la plus rentable de tout cet
audit : elle satisfait à la fois la recommandation 7.3 **et** l'obligation de transparence
de l'article 50 de l'AI Act.

**Manque n° 2 — le consentement à l'enregistrement de la voix.** La recommandation 7.1
dit qu'il ne faut **pas** exiger de consentement spécifique pour l'IA en soin courant…
mais elle réserve un cas, qui est le nôtre :

> « La collecte et l'utilisation d'enregistrements photo, vidéo ou **vocaux** permettant
> l'identification de la personne sont soumises **au consentement** de la personne au
> titre du code civil. »

Oris demande aujourd'hui de cocher « **le patient a été informé** », l'horodate et
l'inscrit au journal d'audit — ce qui est déjà mieux que la plupart. Mais **informer n'est
pas recueillir un consentement**. Il faut : reformuler la case, tracer le consentement
plutôt que l'information, et prévoir le **refus** (une consultation documentée sans
écoute).

**Ce qui est déjà bon :** la traçabilité de l'information (horodatage + audit), et le fait
que le son soit effacé dès la transcription faite — un argument fort pour l'information
générale.

**À faire aussi (vous, aujourd'hui, niveau 1 du guide) :** une affiche en salle d'attente
et une mention dans le livret d'accueil. Le guide donne un modèle de texte.

### 4.8. Décision automatisée et contrôle humain (reco 8.1 à 8.5) — le point fort

Le guide exige une **supervision humaine de toute décision assistée**, adaptée au risque,
et rappelle qu'aucune décision entièrement automatisée n'est permise.

Oris est **conforme par construction** : un document n'est jamais validé tout seul, il
porte la mention « brouillon » tant que le praticien ne l'a pas validé, la validation est
un geste explicite, et le document refuse même la validation s'il contient une phrase non
justifiée. La supervision est « intégrale » au sens de la recommandation 8.2 — 100 % des
sorties passent sous vos yeux.

**Un seul complément :** la recommandation 8.5 demande une **analyse régulière des
incidents**. Oris trace tout mais ne propose aucune revue. Une page « ce qui a été
corrigé ce mois-ci » serait la réponse — et elle existe déjà à moitié dans le module
d'apprentissage.

### 4.9. Traçabilité des usages (reco 9.1 à 9.3) — très bon

| Ce que demande le guide | Oris |
|---|---|
| Conserver la notice d'utilisation | ❌ pas de notice |
| Journalisation conforme à la CNIL, revue régulière des traces | 🟢 journal d'audit, journaux sans donnée patient — revue à organiser |
| Tracer « IA utilisée : oui / non » dans le dossier | 🟠 implicite, à rendre explicite (voir §4.7) |
| Tracer la décision du professionnel de retenir ou non le résultat | 🟢 validation, corrections et apprentissage sont tracés |
| Journaux techniques détaillant chaque analyse (date, cas, résultat, utilisateur) | 🟢 en place (`registry`, versions de modèle et de prompt) |
| **Accès garanti du client aux journaux**, même hébergé chez le fournisseur | ❌ à prévoir contractuellement et techniquement |
| Conserver les résultats du SIA dans le dossier patient, **avec marquage de leur source** | 🟢 conservés et versionnés ; le marquage existe (`generator`) mais n'est pas montré |

C'est le chapitre où Oris est le plus en avance — l'architecture « objet clinique +
preuve par segment » couvre d'emblée ce que d'autres devront ajouter.

### 4.10. Vigilance, maintenance, performances (reco 10.1 à 10.7)

Le guide demande : un responsable des signalements, un circuit d'incident, une procédure
de maintenance écrite, des **audits réguliers de qualité portant notamment sur les faux
négatifs** (« omissions critiques dues à une surconfiance dans l'outil »), un **contrôle
de la dérive du modèle**, des notes de version, et un **plan de continuité en cas
d'indisponibilité**.

C'est, mot pour mot, le **levier 7** de `docs/QUALITE_INTERPRETATION.md` : les outils
existent (bancs d'essai, versions de prompt, corpus), la **routine** n'existe pas. Et le
guide insiste précisément sur l'omission — ce que j'avais identifié comme le trou noir
d'Oris.

**Manque net :** que se passe-t-il quand Oris est indisponible un mardi matin ? Rien
n'est écrit.

### 4.11. Fin de cycle de vie et désinstallation (reco 11.1)

Rien n'existe : pas d'export complet des données d'un cabinet, pas de procédure de sortie,
pas de certificat de suppression. C'est aussi une exigence de la recommandation 2.7.

### 4.12. IA générative (reco 12.1)

Le guide demande de **maîtriser les usages** : sensibilisation, charte d'usage, liste des
pratiques interdites et catalogue d'usages approuvés. Il décrit longuement le risque du
« shadow IT » — les praticiens qui collent des données de patients dans un agent
conversationnel grand public (440 000 connexions en un mois dans un seul CHU).

**Oris est exactement la réponse à ce risque** : un usage encadré, tracé, sans
copier-coller dans un outil grand public. C'est un argument de vente, à condition de le
dire. Les risques listés par le guide — hallucinations, atteinte au secret médical,
injection de requête — sont tous traités par l'architecture d'Oris, mais **rien ne le
documente pour un client**.

---

## 5. Les sept chantiers qui sortent de cet audit

Par rapport valeur / effort.

| # | Chantier | Effort | Pourquoi |
|---|---|---|---|
| 1 | **Mention d'IA dans chaque document** (PDF, texte, courrier) | Petit | Reco 7.3 + AI Act art. 50. La correction la plus rentable |
| 2 | **Consentement à l'enregistrement** au lieu de « patient informé », avec trace du refus | Petit | Code civil, reco 7.1 |
| 3 | **Notice d'utilisation** (destination, limites, populations, contrôle humain, « oraliser l'examen ») | Moyen | Reco 2.1, 4.x, 6.2, 9.1 — exigée par tout acheteur |
| 4 | **Dossier fournisseur** : performances mesurées, biais, flux de données, incidents, impact environnemental | Moyen | Reco 2.1 et 2.2 |
| 5 | **Routine qualité** : banc rejoué à chaque changement, suivi des omissions, notes de version | Moyen | Reco 10.4 à 10.6 — rejoint le levier 7 |
| 6 | **Export complet et procédure de sortie** d'un cabinet | Moyen | Reco 2.7 et 11.1 |
| 7 | **Plan de continuité** : que fait le praticien si Oris est indisponible | Petit | Reco 10.7 |

Les chantiers 1, 2 et 7 peuvent être faits dans la semaine. Les autres sont de la
rédaction, pas du développement.

---

## 6. Ce que vous, Franck, devriez faire dès maintenant

Vous utilisez déjà Oris sur de vrais patients : ces trois points vous concernent
aujourd'hui, pas le jour de la commercialisation.

1. **Appeler votre assureur** (reco 6.1) et faire confirmer par écrit que l'usage d'un
   outil d'IA d'aide à la documentation est couvert par votre RC professionnelle. Gratuit,
   dix minutes.
2. **Afficher l'information en salle d'attente** (reco 7.2), avec le modèle de phrase du
   guide. Je peux vous l'écrire.
3. **Demander le consentement à l'enregistrement**, oralement, et le tracer — en attendant
   que je corrige la case dans l'app.

---

## Source

- [Guide HAS / CNIL, « Accompagner le bon usage des systèmes d'intelligence artificielle en contexte de soins », février 2026 (PDF, 61 pages)](https://www.cnil.fr/sites/default/files/2026-03/guide_has_cnil_recommandations_ia.pdf)
- [Présentation du guide (AP-HP, direction des affaires juridiques)](https://affairesjuridiques.aphp.fr/textes/guide-has-cnil-accompagner-le-bon-usage-des-systemes-dintelligence-artificielle-en-contexte-de-soins-fevrier-2026/)
- [CNIL — IA et santé : développer et évaluer des systèmes d'IA conformes](https://www.cnil.fr/fr/ia-et-sante-developper-et-evaluer-des-systemes-ia-conformes)
