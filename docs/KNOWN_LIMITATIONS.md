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
- Pas de micro : seule une consultation fictive a une « source audio » (M2/M3).
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

