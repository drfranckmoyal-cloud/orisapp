# Changelog

## Pièces jointes et connecteurs — 2026-09-21
- **Le dossier SmileCloud d'un patient se retient.** Un champ à lui sur la fiche — pas le numéro de dossier du cabinet, qui reste où il est. Posé une fois, il évite d'avoir à redemander à chaque fois quel dossier est le bon, et il se détache si ce n'était pas le bon.
- **Les noms se reconnaissent enfin d'une application à l'autre.** « MOREAU Chloé » dans Doctolib et « Moreau Chloe » dans Oris sont le même patient, ordre des mots, accents et casse compris ; la mesure vient de Dental Lens, où elle tourne sur 772 dossiers réels. Mais « Paul » et « Paule » se ressemblent à 95 % et sont deux personnes : dans la zone de doute, Oris demande au lieu de décider. L'écran « Votre journée » s'en sert déjà.
- **Les pièces jointes quittent `Caches`.** Elles vivaient dans `~/Library/Caches/Oris/attachments`, que macOS s'autorise à vider quand il manque de place et qui n'est pas sauvegardé comme le reste : une radio de patient pouvait disparaître sans que personne ne soit prévenu. Elles rejoignent `~/Library/Application Support/Oris/attachments`, auprès des journées. L'audio reste dans `Caches`, où il est à sa place : il est éphémère par décision (D010). Les fichiers déjà rangés ont été déplacés, chacun revérifié par son empreinte avant que l'original ne soit retiré.
- **Aperçu des pièces jointes**, à la manière d'un coup d'œil rapide : un clic ne
  déclenche plus un téléchargement sans prévenir. Les images et les PDF s'affichent ;
  les **empreintes STL se tournent en 3D**, glisser pour pivoter, molette pour
  approcher, sur fond blanc légèrement grisé. Le lecteur STL (binaire et ASCII) et le
  rendu WebGL sont écrits à la main : six cents kilo-octets de bibliothèque pour
  afficher une liste de triangles auraient été de trop. Un format non affichable le dit
  franchement, avec « Ouvrir dans un onglet » et « Télécharger ».
- **Vignette du praticien** sur chaque ligne de consultation — accueil, liste,
  historique patient : deux initiales, le nom complet au survol. Dans un cabinet à
  plusieurs, savoir de qui vient un compte rendu change tout. `EncounterOut` expose
  désormais le praticien.
- L'accès à la **transcription brute** passe en petit, gris et italique : c'est une
  issue de secours, pas une action du quotidien.
- **Les pièces jointes sont sous la main pendant la révision** : une carte dans le rail,
  avec vignettes pour les photos et zone de dépôt resserrée. Une pièce déposée là est
  **rattachée à cette consultation** — tout en restant celle du patient, retrouvable
  depuis sa fiche.
- **L'onglet « Documents » de la fiche patient devient « Pièces jointes »** : ce qu'on
  importe pour s'y référer en rédigeant. Les documents produits par Oris restent visibles
  dans l'historique et dans l'écran Documents du menu — l'onglet ne les répétait plus.
- **Import par glisser-déposer et par bouton.** Formats acceptés : JPEG, PNG, **HEIC**
  et HEIF (l'iPhone par défaut), WEBP, TIFF, **DICOM**, **STL**, **PLY**, OBJ, PDF —
  80 Mo par fichier. Un format inconnu est **refusé**, pas rangé « au cas où » : un
  fichier qu'on ne saura pas rouvrir n'a pas sa place au dossier.
- **Garanties** : le fichier ressort exactement tel qu'il est entré, rien n'est
  recompressé ; le même fichier importé deux fois ne se range qu'une, l'empreinte le
  dit ; un nom de fichier dangereux ne peut pas sortir de son dossier. Et surtout —
  **Oris ne lit pas les pièces jointes** : aucun fait clinique n'en sort, un test le
  vérifie.
- **Modèle** : `attachments` appartient désormais au **patient** (une photo sert à
  plusieurs consultations) et peut être rattachée à l'une d'elles. Le fichier vit dans
  un magasin sur disque, la base garde le nom, la taille, l'empreinte et l'emplacement.
- **Voyant SmileCloud** dans le cadre d'informations : vert connecté, orange non
  connecté. Il lit un vrai réglage, il n'est pas décoratif.
- **Paramètres › Connecteurs** : SmileCloud et Doctolib, leur état et ce qu'ils feront.
  Grisés, en attente.

## Fiche patient — 2026-09-21
- **Une sortie** : « ← Tous les patients » en tête de fiche. On entrait dans un dossier
  sans pouvoir en ressortir.
- **Le cadre d'informations est une seule grille**, pas trois colonnes côte à côte : les
  cellules d'une rangée partagent leur hauteur, donc les filets se poursuivent d'un bout
  à l'autre. Trois colonnes empilées donnaient des séparateurs décalés.
  Cinq informations seulement — nom, naissance, courriel, correspondants, dernière
  consultation — colonne d'intitulés teintée, bordure de 2 px, fond dégradé : l'identité
  du patient se détache du reste de la page.
- **Nom de famille en capitales** (`nomPatient`), partout où un patient s'affiche. C'est
  un affichage : la casse saisie reste intacte en base, pour les particules et pour le
  jour où la convention changera.
- **Courriel du patient** : colonne `patients.email`, champ à la création, lien
  `mailto:` sur la fiche.
- **La note se dicte** : bouton micro dans le champ. Le son part dans la requête, est
  transcrit, et n'est **jamais conservé** — ni en base, ni sur disque. Le texte dicté
  **s'ajoute** à ce qui est écrit, il n'efface rien, et le praticien relit avant
  d'enregistrer. Route `POST /patients/{id}/note/dictation`.
- **« Votre journée »** entre au menu comme chantier à venir : extraction des
  rendez-vous Doctolib, création automatique des dossiers, écoute démarrée d'un geste —
  avec ce qu'il faudra régler avant (accès éditeur, cadre juridique, doublons).
  L'accueil reprend son titre « Accueil ».

## Marque arrêtée — 2026-09-20
- **Slogan : « Vous soignez. Oris documente. »** Il dit la répartition des rôles en
  quatre mots et met le praticien en premier. Il vit sous le logo dans la barre de
  gauche, dans le titre de la page, et partout ailleurs.
  *« Votre temps reste au soin. »* a été écarté : la meilleure idée, mais il ne dit pas
  ce que fait Oris — un slogan qu'il faut expliquer n'est pas encore un slogan.
- **Texte de présentation** de référence dans `docs/POSITIONNEMENT.md`, avec une
  précision sur ce que « adaptatif » recouvre : le dictionnaire, les mots préférés et
  le style du praticien sont transmis à chaque traitement, et ce qu'il corrige reste
  dans son propre profil.
- **Le nom est vectorisé** — Fraunces 600, taille optique 48, axe WONK éteint, crénage
  de la police. Plus aucun fichier de la marque ne dépend d'une police installée : les
  verrouillages s'impriment. 50 PNG dans `design/marque/png/`.

## Direction visuelle appliquée — 2026-09-20
La direction 4b passe des maquettes au produit, et devient le système verrouillé
(`docs/DESIGN_SYSTEM.md`, `design/tokens.json`).

- **Palette** : neutres chauds et vert profond, à la place du bleu. Quinze jetons
  regénérés vers le CSS du site et le Swift de l'iPhone.
- **Polices** : **Manrope** pour l'interface, **Fraunces** pour le nom « Oris ».
- **Relief** : trois couches d'ombre plus un filet de lumière sur toute surface posée,
  ombre interne sur les surfaces creusées. Une ombre plate inventée sur place est
  désormais un écart au système.
- **Barre de gauche** : bloc vert plein ; le logo est une **plaque crème posée dessus**,
  cliquable, qui ramène à l'accueil ; les entrées portent des pictogrammes et chacune
  sa surface en relief ; l'entrée active porte un repère argile sur le flanc. Le
  praticien se choisit en bas, dans un menu déroulant ; « Nouveau praticien » y attend
  son tour.
- **Accueil** : plus de « Bonjour Docteur ». Un **grand bouton vert** pour commencer une
  consultation, dont le logo s'anime au survol ; la semaine en barres ; la saisie évitée
  **avec sa méthode de calcul affichée** ; ce qui attend ; ce qu'Oris a appris.
- **Fiche patient** : un vrai **cadre d'informations** en deux colonnes à la place des
  bulles éparpillées ; la note y est logée, discrète, enregistrée en quittant le champ ;
  l'historique en dessous, lisible et cliquable, avec un accès minuscule à la
  **transcription brute** (nouvel écran). Le plan de traitement quitte la fiche : il
  appartient à la consultation.
- **Correspondants** : entrée de menu et écran « chantier à venir », qui dit ce qu'il
  fera et ce qui manque — plutôt qu'un lien mort.
- **Paramètres** : liste des praticiens du cabinet, et création d'un profil grisée.
- **Marque en PNG** : `design/marque/png/`, 35 fichiers de 16 à 1024 px, produits par
  `scripts/export_marque.py` — dessinés directement, sans dépendre d'un moteur SVG.
  Favicon, icône d'iPhone et symboles du site remplacés.

## Refonte produit (7) — 2026-09-20 — note administrative sur la fiche patient
Dernier champ manquant du §9. « Note **administrative** courte », et les trois mots
comptent :

- **administrative** : un rappel d'organisation (horaires, rappel à passer, préférence),
  pas un dossier médical. L'écran le dit en toutes lettres : « Oris ne la lit pas et ne
  la reprend dans aucun compte rendu. » Un test le prouve — une note reconnaissable
  n'apparaît ni dans la transcription, ni dans les faits, ni dans un document ;
- **courte** : 500 caractères, refusés au-delà. Un champ long inviterait à y écrire du
  clinique qui ne serait jamais repris nulle part ;
- **facultative** : vide par défaut, elle ne réclame rien.

Colonne `patients.note`, champ dans la création et la modification, carte en tête de la
fiche patient. Variante compacte de la zone de texte dans le système de composants : la
hauteur du document éditable écrasait la fiche.

## Refonte produit (6) — 2026-09-20 — la transcription en continu
Dernier écart technique du cadrage (§11, §14.1) : l'adaptateur WebSocket existait mais
n'était branché à aucun écran.

- **Panneau « Ce qu'Oris entend »**, replié par défaut sous les boutons de l'écoute. Il
  affiche les paroles à mesure : en italique pâle tant qu'elles sont provisoires, en
  encre pleine une fois confirmées — un résultat acquis ne redevient jamais flou.
- **Ce texte n'est jamais le dossier.** Le cadrage l'exige (§14.1) et un test le tient :
  un fournisseur de direct qui produit un texte reconnaissable ne laisse **aucune trace**
  dans la transcription enregistrée ni dans les faits cliniques. La finalisation refait
  la transcription sur l'enregistrement complet.
- **Le chemin durable de l'audio n'est pas touché** : les segments continuent d'arriver
  par `PUT /audio/chunks/{n}`, avec empreinte et idempotence. Le direct **écoute** ce
  flux, il ne le remplace pas. S'il tombe, l'écran le dit et précise que
  *l'enregistrement continue* ; la consultation se termine normalement.
- Derrière le drapeau `ENABLE_LIVE_TRANSCRIPT` (§85), éteint par défaut.
- Route `GET /encounters/{id}/live`.

**Correction au passage** : la liaison temps réel échouait sur ce Mac par
`CERTIFICATE_VERIFY_FAILED` — le Python installé depuis python.org n'a pas de magasin
d'autorités système. Les WebSockets utilisent désormais `certifi`, comme les appels HTTP.

## Refonte produit (5) — 2026-09-20 — l'infrastructure d'apprentissage
Le cadrage (§202, §205) interdisait de construire une V1 non apprenante puis d'ajouter
ces mécanismes plus tard. Les huit tables manquantes existent, et la plupart sont
écrites par le produit lui-même.

- **`prompt_versions` / `model_versions`** : chaque traitement inscrit la consigne et le
  modèle qui ont réellement servi, avec l'**empreinte sha256 du texte de consigne** — une
  retouche silencieuse se voit. Visibles dans **Paramètres › Moteurs** : « Extraction
  clinique — anthropic · claude-sonnet-5/extraction-fr-5 · consigne extraction-fr-5 ».
- **`model_runs`** : un appel fournisseur = une ligne (durée, état, code d'erreur,
  compteurs). **Jamais de contenu patient**, pas même en métadonnée (§56) — un test
  compare la trace à la transcription pour s'en assurer. Un transcript vide est tracé
  comme un échec, pas comme une réussite.
- **`practitioner_learning_profiles`** : le profil du contrat, recalculé à chaque
  changement de préférence ou de dictionnaire. C'est un **miroir**, pas une seconde
  source ; un terme désactivé en sort aussitôt. Route `GET /me/learning/profile`.
- **`dataset_versions` / `evaluation_runs`** : le banc d'essai d'extraction écrit sa
  mesure en base, avec le jeu de données cité et sa nature (jouée ou réelle). La porte
  de sortie se ferme sur une **régression critique**, même si la moyenne s'améliore.
- **`templates` / `attachments`** : prévues par le cadrage, créées, inactives en V1 —
  comme §205 l'autorise explicitement.

## Refonte produit (4) — 2026-09-20 — les écrans restants
- **accueil (§8)** : la **recherche patient** qui manquait — on tape un nom, on tombe sur
  la fiche.
- **« Oris apprend de vous » (§124)** : les **sept sections** du cadrage, et plus trois.
  - *Oris a appris* : la lecture en clair de ce qui est actif (« ✓ Vous dites « avulsion »
    plutôt que « extraction » »), avec un bouton **Exporter** — préférences et dictionnaire
    dans un fichier, rien n'est enfermé dans Oris ;
  - *Matériaux reconnus* et *Termes appris* séparés, et le formulaire demande la nature ;
  - *Ce que vous corrigez le plus souvent* : les corrections comptées, en français
    (« Statut de traitement corrigé — proposé → accepté »). Oris **montre**, il n'en déduit
    rien ;
  - *Réinitialiser* : un champ, ou tout. La remise à zéro ne touche jamais au dictionnaire
    saisi à la main.
- **API** : `POST /me/preferences/reset`, `GET /me/learning/corrections`,
  `GET /me/learning/export`.
- Le détail d'une correction ne montre que le geste et son sens : jamais une phrase du
  dossier. Un test le vérifie.

## Refonte produit (3) — 2026-09-20 — points marqués et fiabilité des faits
- **« Marquer un point » (§11)** : pendant l'écoute, un bouton discret pose un repère
  temporel. Nouvelle table `encounter_marks`, routes `POST`/`GET /encounters/{id}/marks`.
  Un repère n'est **jamais** une donnée clinique : il n'entre pas dans l'objet, il sert à
  retrouver le moment. À la relecture, un onglet **Points marqués** montre chaque instant
  avec ce qui se disait autour (20 s avant, 5 s après) ; si la transcription a échoué, les
  repères restent affichés — le geste du praticien n'est pas perdu.
- **graduation de fiabilité (§31)** : chaque fait porte « fiable » ou « à vérifier », avec
  la raison au survol (voix non identifiée, terme inconnu, incertitude clinique,
  reconnaissance peu sûre) et le décompte en tête de liste.
- **intégration continue réparée** : le test de conversion audio exigeait `afconvert` ou
  `ffmpeg` — présents sur macOS, absents de la machine GitHub. Le test se saute sans
  convertisseur et la chaîne installe `ffmpeg`. L'écran « Nouvelle consultation » cassait
  la compilation de production (`useSearchParams` sans frontière Suspense) : repris avec
  les composants maison et une frontière Suspense.
- **onglets** : ils passent à la ligne au lieu de déborder du rail.

## Refonte produit (2) — 2026-09-20 — identité visuelle appliquée
- le **symbole d'Oris** entre dans l'application : dans le menu (version blanche sur fond
  bleu profond, comme l'icône alternative de la planche) et au centre de l'écran d'écoute,
  où il respire pendant la capture — c'est la seule animation du produit ;
- **favicon** : le symbole blanc sur bleu profond ;
- symbole extrait du logo de marque et recadré sur son encre (`assets/oris-symbole.png`),
  sans redessiner la marque.

## Refonte produit (1) — 2026-09-20
Première passe de la refonte décrite dans `docs/AUDIT_DESIGN.md` et `docs/ETAT_REEL.md`.

- **fondations** : palette bleue figée, police Inter réellement chargée, jetons
  sémantiques, bibliothèque de composants (bouton, carte, en-tête, pastille, onglets,
  état vide, squelette, étapes, barre, zone de texte) ;
- **accueil** : tableau de bord — à relire, aujourd'hui, terminées, à reprendre ;
- **patients** : recherche insensible aux accents, création complète, et **fiche patient**
  (consultations, documents, plan de traitement) ;
- **écran d'attente** (S06) : trois étapes réelles lues en base (`/progress`), sans
  pourcentage inventé ;
- **révision** (S08) : rail à onglets À vérifier / Données cliniques / Historique, source
  d'une phrase par-dessus le rail, faits en français (`/ontology/concepts`) ;
- **édition manuelle du texte** (§48) et **raccourcir** (§53) ;
- **plan de traitement** (§34) : ajouter, retirer, monter, descendre — la séquence
  devient explicite quand l'ordre est décidé ;
- **Documents** et **Paramètres** : les deux écrans manquants ;
- tests : API 278, web 47.

## Cadre des séances jouées — 2026-09-20
- `docs/consentement/note-information.md` et `consentement-participant.md` : ce qui est
  enregistré, ce qui ne l'est pas, qui le traite (y compris hors UE), combien de temps,
  et comment retirer son consentement ;
- `docs/PROTOCOLE_ENREGISTREMENT.md` : matériel, six situations à jouer dont une
  « consultation piège » qui teste correction de dent, négation, incertitude, parole du
  patient, acte futur et refus ; nommage, transmission, suppression ;
- `scripts/prepare_recordings.py` : conversion en 16 kHz mono, lecture des transcriptions
  de référence (« praticien | … »), écriture du manifeste — **refus** d'écrire un jeu
  sans consentement référencé ;
- tests : API 271.

## M11 — 2026-09-20 — mise en situation clinique
- **mode ombre** : Oris travaille en parallèle du praticien pour être comparé ; ses
  documents ne peuvent être ni validés ni exportés, la règle est appliquée côté serveur ;
- **porte d'entrée en bêta exécutable** (`scripts/beta_gate.py`) : elle refuse tant que
  les fournisseurs ne sont pas revus, que les flux de données ne sont pas documentés, que
  des séances jouées par des praticiens manquent, ou que l'hébergement agréé n'est pas là ;
- **inventaire des flux fournisseurs** (`docs/VENDORS.md`) : finalité, données envoyées,
  région, conservation, entraînement, sous-traitants, DPA — et ce qui ne sort jamais ;
- **contrôle des jeux d'enregistrements** (`scripts/check_dataset.py`) : format,
  consentement documenté et référencé, rôles présents ;
- correction d'interface : un `hidden` était écrasé par un `display` de classe ;
- tests : API 266, web 47.

## M10 — 2026-09-20 — sécurisation
- **jetons d'accès** par praticien (`Authorization: Bearer`), empreinte scrypt salée,
  révocation immédiate ; `scripts/issue_token.py` pour créer, lister, révoquer ;
- **aucune route métier sans jeton** hors développement : il n'existe pas de mode ouvert ;
- **journal d'audit lisible** (`GET /audit`) : identifiants, actions, statuts et versions,
  jamais une phrase clinique — un test échoue si un mot clinique y entre ;
- défaut corrigé : les actions du système (génération, purge) étaient enregistrées sans
  organisation et n'apparaissaient donc pas dans le journal ;
- **purge du son rejouable et observable** (`POST /maintenance/audio-purge`) : une panne
  de stockage n'interrompt pas la passe et ressort dans le rapport ;
- `docs/SECURITY.md` distingue désormais ce qui est fait de ce qui relève de
  l'hébergement (MFA, chiffrement au repos, sauvegardes, HDS, tests de charge) ;
- migration 0005 ; tests : API 255.

## M9 — 2026-09-20 — personnalisation
- **dictionnaire du praticien** (`learning.glossary_terms`, migration 0004) : marques,
  produits et termes propres au cabinet, soufflés à la transcription **et** à
  l'extraction — ils ne l'étaient pas ;
- **préférences de rédaction** : mot préféré par concept (« avulsion » pour
  « extraction ») et compte rendu concis (les préfixes qui répètent le titre de section
  disparaissent, jamais une nuance clinique) ;
- **suggestions** : après deux corrections dans le même sens, Oris propose une règle —
  et ne l'applique jamais de lui-même ;
- **tout est réversible** : désactiver un terme, retirer un mot préféré, revenir au
  format standard ;
- écran « Oris apprend de vous » sur le site ;
- `material_name_correction` : corriger un nom de produit alimente les suggestions ;
- tests : API 245.

## M8 — 2026-09-20 — correction dictée
- une phrase du praticien devient un **patch structuré** de l'objet clinique, jamais une
  retouche du texte : remplacement de dent, ajout de dent, retrait d'un élément,
  changement de statut d'un traitement ;
- **aperçu d'abord** : Oris montre ce qu'il a compris et l'impact ; appliquer demande une
  confirmation explicite et la version d'objet attendue ;
- ce qui est ambigu n'est pas deviné : la commande revient avec la raison et les éléments
  possibles, écrits en français ;
- une préférence de rédaction (« plus court ») est distinguée d'une correction clinique :
  elle est retenue pour l'apprentissage et ne touche pas au dossier (§46) ;
- `POST /encounters/{id}/corrections/voice` : l'audio est transcrit dans la requête puis
  oublié, il n'entre jamais dans le stockage de la consultation ;
- sur le site : dicter au micro ou écrire, relire le patch, appliquer ;
- tests : API 239, web 47.

## M7 — 2026-09-19 — comptes rendus opératoires
- les sept modèles de la spécification (composite, esthétique direct, facettes
  préparation, facettes collage, usures additives, avulsion, chirurgie mineure) : des
  **emplacements de preuve ordonnés**, jamais des paragraphes préremplis ;
- un emplacement se renseigne s'il a été dicté dans l'acte, ou par un fait dit pendant
  l'intervention (la phrase cite alors ce fait) ; rien d'autre ne le remplit ;
- un emplacement important resté vide **alerte** (« champ important non dicté ») et n'est
  jamais complété ; un acte seulement prévu n'est pas interrogé sur ses matériaux ;
- le compte rendu de soins n'est jamais produit d'office : le site propose « un acte a
  été détecté », le praticien décide (§81) ; une fois demandé, il suit les corrections ;
- invite d'extraction `extraction-fr-5` : le modèle connaît les emplacements de chaque
  type d'acte et vise les bonnes clés ;
- vérifié de bout en bout sur quatre types d'acte, transcription et extraction réelles ;
- tests : API 222.

## Habillage des documents — 2026-09-19
- un modèle d'impression par type : compte rendu de consultation, plan de traitement,
  **compte rendu de soins**, **courrier d'adressage** (formule d'appel, politesse,
  signature), **résumé patient** (texte plus grand, mention de remise) ;
- en-tête habillé : logo, nom et coordonnées du cabinet, praticien, patient, date, rappel
  de validation ; couleurs du système de design ;
- identité du cabinet configurable dans `services/api/config/cabinet.json` ; sans ce
  fichier, l'en-tête reste sobre et le document sort quand même ;
- dépendance `pillow` (logo) ;
- tests : API 208.

## M6 (2/2) — 2026-09-19 — plan de traitement en cartes
- chaque élément du plan devient une carte : dents, intitulé, statut, motif, faits
  d'appui cliquables, alternatives, préalables, incertitudes ; le statut se change sur
  la carte, et c'est toujours le dossier clinique qui est modifié ;
- l'historique dit ce qu'une correction a changé (« proposé → accepté ») ;
- logique de correction mutualisée (`useCorrection`) entre les écrans qui corrigent ;
- tests : web 43.

## M6 (1/2) — 2026-09-19 — sortie des documents
- `GET /documents/{id}/export?format=pdf|text|structured` : PDF A4 (identité du cabinet
  et du praticien, patient, date, type, mention de validation, pagination), texte brut,
  texte structuré ;
- sur le site : **Copier pour le dossier** et **Exporter en PDF**, avec repli sur une
  zone de texte sélectionnable si le navigateur refuse le presse-papiers ;
- un brouillon peut sortir mais porte la mention « non validé », et son statut ne change
  pas ; seul un document validé passe à `exported`, et la consultation passe à
  `exported` quand tous ses documents en sont sortis ;
- le nom du fichier ne porte pas le nom du patient ;
- dépendance `reportlab` ;
- tests : API 202, web 35.

## Vocabulaire (2) — 2026-09-19 — termes dictés par le praticien
- 42 termes intégrés depuis la dictée du 19/09 : **269 termes**, 16 thèmes (nouveau
  thème « Matériaux, produits et instruments ») ;
- cinq noms propres et sigles ajoutés au glossaire envoyé à la transcription (Astéria,
  SmileCloud, peroxyde de carbamide, zircone, DVO) : ce glossaire est plafonné à 50
  termes, contrairement au vocabulaire de rédaction qui n'a pas de limite ;
- « adressage à un confrère » devient « adressage à un confrère ou une consœur ».

## Vocabulaire — 2026-09-19
- vocabulaire clinique porté de 50 à **227 termes**, classés en 15 thèmes (motif,
  symptômes, examen dentaire, usures et esthétique, parodonte et occlusion, examens
  complémentaires, diagnostics, options, projet esthétique, actes directs, prothèse,
  chirurgie, informations au patient, antécédents, suivi) ;
- `docs/VOCABULAIRE.md` : la liste lisible par le praticien, produite depuis le code par
  `scripts/vocabulaire.py`, avec un tableau « à ajouter » par thème ; un test échoue si
  la liste dérive du code ;
- effet mesuré sur la consultation de démonstration : « À rédiger : élément « crowns »
  non reconnu » devient « Option écartée : couronnes », et les deux documents passent de
  1 à 0 problème de validation ;
- tests : API 196.

## M5ter — 2026-09-19 — la chaîne complète micro → compte rendu
- une consultation enregistrée part désormais chez Deepgram puis chez Claude :
  vérifié de bout en bout sur un vrai fichier audio poussé comme le fait le micro du
  site (4 segments de 2 s) → transcription, audio purgé, faits extraits, compte rendu
  rendu en 5 s, zéro problème de validation, négation conservée ;
- une consultation fictive ne part plus chez un fournisseur réel : son « enregistrement »
  est une étiquette que seul le fournisseur factice sait lire (`synthetic_speech_to_text`) ;
- nouvelle alerte `SPEAKER_ROLES_UNKNOWN` (à vérifier, non bloquante) quand un segment
  reste sans rôle : sans voix séparées, rien ne garantit qu'une parole du patient n'a pas
  été écrite comme un constat du praticien (invariant 5) ;
- banc d'essai STT : nouvelle mesure `single_voice_rate`. Le score « locuteurs bien
  séparés » récompensait un fournisseur qui met tout le monde dans la même voix —
  mesuré : **72 % des enregistrements reviennent d'une seule voix** ;
- une voix unique n'est plus traitée comme « une seule personne » : chaque passage est
  jugé sur ses propres mots, et reste sans rôle s'il n'a rien de décisif ;
- Deepgram reprend deux fois une panne passagère (réseau, 429, 5xx, 408) : le banc du
  19/09 perdait 5 consultations sur 30 pour des incidents de quelques secondes ;
- le site affiche les alertes « à vérifier » (jusqu'ici seules les alertes critiques
  étaient visibles : la nouvelle alertes sur les voix serait passée inaperçue) ;
- imports différés des adaptateurs STT dans la fabrique (dépendance circulaire) ;
- tests : API 191, web 33.

## M5bis — 2026-09-18 — les six échecs compris et corrigés
- diagnostic : les six consultations refusées par Sonnet ne l'étaient pas de façon
  systématique — rejouées, elles aboutissent. Le modèle varie d'un appel à l'autre, et
  deux d'entre elles n'aboutissent qu'au **troisième** essai ;
- nombre d'essais expliqués porté de deux à trois ; une coupure réseau, un quota (429)
  ou une erreur serveur repasse le même appel deux fois (1 s puis 4 s) au lieu de perdre
  la consultation ;
- un échec dit désormais **ce qui** a été refusé : `ExtractionUnavailable` porte des
  `details`, dont `rule_codes()` n'extrait que les noms de règles (aucun contenu clinique) ;
- défaut corrigé : une panne du fournisseur d'extraction remontait en erreur 500 au lieu
  de classer la consultation en `generation_failed` ; le pipeline l'attrape et affiche
  les règles refusées ;
- vérifié : les six consultations aboutissent (2 au 1er essai, 2 au 2e, 2 au 3e) ;
  tests API 188.

## M5 — 2026-09-18 — Clinical extraction
- extraction clinique réelle par Claude derrière `ClinicalExtractionProvider` : sortie
  imposée par un outil dont le schéma vient des contrats d'Oris, provenance posée par
  Oris, consignes versionnées (`extraction-fr-4`) ;
- une sortie invalide ou contraire aux règles cliniques donne droit à des essais
  expliqués par le résolveur (deux à l'origine, trois depuis M5bis), puis elle est
  rejetée — jamais corrigée ;
- garde-fou `ALLOW_EXTERNAL_LLM` + clé locale ; tests forcés en mode factice ;
- banc d'essai extraction (100 consultations du corpus, 2 modèles comparés) :
  Sonnet 5 → 94 % d'extractions abouties, 0 % de rejet par le résolveur, négations
  98,6 %, temporalité 98,3 %, prévu/réalisé 94,2 %, 3,2 centimes par consultation ;
  Haiku 4.5 → 69 % d'extractions abouties, 1,5 centime ;
- règle corrigée : un emplacement d'acte est valide s'il a été **prononcé** dans les
  segments cités ;
- démonstration dans l'application : consultation fictive traitée par le vrai modèle,
  compte rendu « Suspicion de fissure (16), non confirmée », zéro problème de validation ;
- tests : API 186, web 33, iOS 39.

## M4bis — 2026-09-18 — premier banc d'essai réel
- Deepgram Nova-3 mesuré sur les 100 consultations synthétiques (35 min d'audio) :
  numéros de dent 100 % (243 mentions, 0 inventé), négations 100 %, WER 8,2 %,
  termes dentaires 81 % (dont +13,4 points apportés par le glossaire), séparation
  des voix 86,9 %, rôles 83,7 %, délai médian 1,7 s, 100 % de requêtes abouties ;
- conformité non évaluée → aucun fournisseur retenu (gate).

## M4 — 2026-09-17 — STT benchmark adapter
- adaptateurs Azure AI Speech (transcription rapide `2025-10-15` + SDK temps réel
  `ConversationTranscriber`) et Deepgram Nova-3 (fichier + WebSocket) derrière
  `SpeechToTextProvider` / `StreamingSpeechToTextProvider` ;
- diarisation : étiquettes brutes séparées, rôles praticien/patient attribués par
  heuristique prudente (`unknown` si doute) ;
- glossaire dentaire (≤ 50 termes) poussé en phrase list / keyterms ;
- temps réel Deepgram : reconnexion avec renvoi de l'audio non confirmé ;
- garde-fou : STT externe seulement avec `ALLOW_EXTERNAL_STT=true` et clés locales ;
- panne du fournisseur : `STT_UNAVAILABLE`, audio conservé, bouton « Relancer le
  traitement » sur le web ;
- numéros de dent dits en lettres → chiffres FDI (`domain/dental_numbers.py`) ;
- banc d'essai : jeu synthétique (100 consultations, voix macOS), métriques de la note
  technique, score pondéré, conformité en préalable, `EvaluationRun` + rapport français,
  contrôle hors ligne `check` ;
- tests : API 171, web 33, iOS 39.

## M3 — 2026-09-17 — iOS audio capture
- écoute iPhone : AVAudioSession (parole, micro AirPods) + AVAudioEngine, même
  contrat audio que le web (PCM 16 kHz mono, segments de 2 s, SHA-256) ;
- tampon local chiffré AES-GCM (clé dans le trousseau de l'appareil, fichiers
  protégés, hors sauvegardes), segments effacés dès l'accusé de réception ;
- appel / Siri : écoute suspendue sans reprise automatique, durée signalée comme trou ;
- AirPods retirés ou nouvelle entrée : capture relancée, trou signalé au-delà d'1 s ;
- écran verrouillé : écoute poursuivie (mode audio en arrière-plan) ;
- coupure réseau : capture continue, renvoi dans l'ordre, relance immédiate au retour
  du réseau ; « Terminer malgré tout » ;
- app fermée : segments chiffrés renvoyés à la réouverture, trou `app_terminated`,
  reprise ou fin proposées ;
- micro refusé : explication et accès aux Réglages ;
- écrans : nouvelle consultation (patient), pré-écran, écoute plein écran ;
- serveur : motifs de trou `audio_interruption`, `route_change`, `app_terminated` ;
- tests : API 129, web 33, iOS 39.

## M2 — 2026-09-17 — Web audio capture
- capture micro dans le navigateur (AudioWorklet), PCM 16 kHz mono en segments de 2 s
  horodatés à l'échantillon ;
- envoi ordonné et idempotent (numéro de séquence, SHA-256), nouvelles tentatives
  illimitées pendant une coupure réseau, suppression locale après accusé de réception ;
- pause / reprise (micro libéré pendant la pause), durée maximale 90 min avec alerte à 80 ;
- micro perdu, page rechargée, segments non envoyés : trous déclarés → alerte critique
  `AUDIO_GAP` ; fin d'écoute refusée tant que des segments manquent, sauf « Terminer
  malgré tout » explicite ;
- pré-écran : patient, autorisation micro, réseau, information patient paramétrable
  (`PATIENT_INFORMATION_MODE`) ;
- audio éphémère purgé après traitement, métadonnées de réception conservées ;
- source de son de test sans micro (local uniquement) ;
- migration 0003 : `audio_sessions`, `audio_chunks` ;
- tests : API 126, web 33 (dont capture sans navigateur), iOS 14.

## M1 — 2026-09-17 — Synthetic vertical slice
- parcours complet sur consultation fictive : patient → consultation → transcript →
  faits → objet clinique versionné → compte rendu + plan → validation explicite ;
- résolveur déterministe : sortie d'extraction rejetée (jamais corrigée) si preuve
  inventée, acte futur « réalisé », impression du patient promue en constat ou
  diagnostic, incertitude perdue, option acceptée sans décision, matériau non
  prononcé, ou fait prétendument validé par le praticien ;
- rédaction française par gabarits depuis l'objet seul ; chaque phrase cite ses faits ;
- validateur factuel (phrase sans appui, dent non portée, « Réalisé » sans acte réalisé,
  fait non restitué, concept inconnu) ;
- coupure audio : alerte critique, document déclaré non exhaustif, validation
  conditionnée à une reconnaissance explicite ;
- corrections structurées (dent, fait, statut du plan, ajout, retrait) : nouvelle
  version de l'objet → documents périmés → régénération ; historique append-only ;
- LearningEvents dans le schéma `learning` (corrections, alerte reconnue, validation
  sans modification) ;
- web : écrans patients, consultations, nouvelle consultation fictive, révision
  (source de chaque phrase, faits, corrections, historique, validation) ;
- iPhone : liste des consultations et consultation en lecture (Compte rendu | Plan |
  À vérifier) ;
- contrats : OpenAPI exporté, types web générés, réponses réelles figées pour les
  tests iOS ;
- migration 0002 : `encounter_object_versions`, phrases et problèmes des documents ;
- tests : API 104, web 13, iOS 14.

## M0 — 2026-09-17 — Repository & contracts
- monorepo : `services/api` (FastAPI), `apps/web` (Next.js), `apps/ios` (SwiftUI) ;
- types Python/TypeScript/Swift générés depuis `schemas/` (`scripts/generate_contracts.py`, vérifié en CI) ;
- tokens visuels web/iOS générés depuis `design/tokens.json` ;
- PostgreSQL + migration Alembic initiale : dossier clinique et learning store (schéma `learning` séparé) ;
- valeurs d'enum des contrats imposées par contraintes CHECK en base ;
- interfaces des 4 fournisseurs IA + implémentations mock ; tout fournisseur non-mock refusé ;
- journalisation JSON en liste blanche (aucun nom, transcript, message d'exception, query string) ;
- `GET /health`, `GET /health/ready` ;
- coquilles web et iPhone en français affichant l'état du serveur ;
- CI GitHub Actions : contrats, API (PostgreSQL), web ; iOS sur changement ;
- tests : API 45, web 8, iOS 9.

## v1.2 — 2026-09-16
- final audit;
- Oris naming frozen;
- visual identity frozen for V1;
- machine-readable schemas added;
- Claude Code starter instructions added;
- synthetic 100-case corpus added;
- technical provider benchmark added;
- learning architecture clarified vs MVP scope.
