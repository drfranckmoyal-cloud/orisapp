# Known Limitations — handoff baseline

- No real audio benchmark has been run yet.
- Generated visual identity assets are concept PNGs, not vector production masters.
- HDS/legal architecture must be finalized before real patient data.
- No PMS integration in V1.
- No longitudinal patient-context injection in initial release.
- The 100-case corpus is synthetic and must later be complemented by professionally simulated and governed real-world evaluations.

## Après M0 (2026-09-17)

- Pas d'authentification ni de MFA : l'API n'est utilisable qu'en local.
- `uniqueItems` des schémas n'est pas exprimé par les modèles Pydantic/Swift/TS ;
  seule `validate_contract` (jsonschema) le contrôle.
- Identifiant d'app iOS provisoire `fr.oris.app` : à fixer avant TestFlight.
- Texte blanc sur Oris Blue (#3B82F6) : contraste 3,7:1, conforme AA seulement en grand
  texte ; le bouton principal est donc en 19 px gras. À revoir avec le design final.
- App iPhone vérifiée par tests unitaires uniquement (pas de capture sur simulateur en M0) ;
  pas encore de tests d'interface.
- Base embarquée (`pixeltable-pgserver`) réservée au développement local.
- CI jamais exécutée avant le premier push de M0 : à confirmer sur GitHub.

## Après M1 (2026-09-17)

- **Extraction non réelle** : le mock rejoue les faits attendus du corpus pour un
  transcript reconnu à l'identique. Les tests A–I prouvent la conservation des axes
  jusqu'aux documents et le rejet des sorties fautives, pas la qualité d'extraction
  depuis la parole (M5).
- Rédaction par gabarits semi-télégraphiques : fidèle mais peu naturelle ;
  préférences de longueur et de style non appliquées (M9). Les objectifs (`goals`)
  du plan ne sont pas rédigés faute de faits d'appui dans le schéma.
- Libellés français limités aux concepts du corpus (`ontology/labels.py`) ; un concept
  inconnu apparaît « À rédiger », jamais deviné.
- Le validateur repère les numéros de dent par motif : « contrôle à 15 jours »
  serait pris pour la dent 15 (faux positif bloquant, jamais un faux négatif).
- Correspondance emplacement opératoire → concept approximative (nom inclus) en
  attendant les gabarits M7.
- Pas d'édition libre du texte (§48) ni de correction vocale (M8) : toute validation
  est enregistrée « sans modification ».
- Pas d'export PDF / texte (M6).
- Traitement synchrone dans la requête HTTP (pas de worker).
- iPhone en lecture seule : ni correction ni validation depuis l'app.
- Identité de démonstration unique, sans authentification : `local`/`test` seulement.

## Après M2 (2026-09-17)

- **Aucune transcription de l'audio réel** : une consultation au micro se termine en
  « Transcription impossible » (M4). L'audio est reçu, contrôlé puis purgé.
- Purge immédiate après traitement, même en cas d'échec de transcription : pas de
  nouvelle tentative possible sur le même audio (politique à revoir avec le STT réel).
- Segments conservés en mémoire du navigateur seulement : une fermeture d'onglet perd
  ce qui n'était pas encore envoyé (signalé comme trou à la reprise).
- Stockage serveur transitoire non chiffré (`~/Library/Caches/Oris/audio`) : dev
  uniquement ; stockage HDS chiffré requis avant tout audio réel de patient.
- Pas de WebSocket ni de transcription en direct.
- Rééchantillonnage par moyenne, sans filtre anti-repliement soigné.
- Capture micro réelle non vérifiée dans le navigateur intégré (micro bloqué) : testée
  avec le son de test et par tests unitaires ; à essayer dans Chrome ou Safari.
- Choix du périphérique d'entrée non proposé.

## Après M3 (2026-09-17)

- Écoute iPhone vérifiée par tests (entrée audio simulée) et compilation, **pas à
  l'écran ni sur un vrai iPhone** : accès au simulateur non accordé ; appels, AirPods
  et verrouillage réels restent à éprouver sur appareil (§70).
- Sur un vrai iPhone, `localhost` ne désigne pas le Mac : fixer `ORIS_API_URL`
  (adresse du Mac sur le réseau local) ; l'envoi en HTTP clair exigera une exception
  ATS en développement, et HTTPS en production.
- Le tampon chiffré survit à la fermeture de l'app, mais une désinstallation efface la
  clé : les segments non envoyés sont alors perdus (signalés comme manquants).
- Pas de choix manuel de l'entrée audio ; pas de transcription en direct.
- La durée d'une interruption après fermeture de l'app est estimée depuis la dernière
  réception serveur (horloges différentes, ordre de grandeur seulement).

