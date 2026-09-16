# Known Limitations — handoff baseline

- No real audio benchmark has been run yet.
- Generated visual identity assets are concept PNGs, not vector production masters.
- HDS/legal architecture must be finalized before real patient data.
- No PMS integration in V1.
- No longitudinal patient-context injection in initial release.
- The 100-case corpus is synthetic and must later be complemented by professionally simulated and governed real-world evaluations.

## Après M0 (2026-09-17)

- Pas d'authentification ni de MFA : l'API n'est utilisable qu'en local.
- Aucune route métier (patients, consultations, documents) : prévues en M1.
- Les fournisseurs mock ne font aucune extraction : ils rejouent des faits scriptés.
- `uniqueItems` des schémas n'est pas exprimé par les modèles Pydantic/Swift/TS ;
  seule `validate_contract` (jsonschema) le contrôle.
- Identifiant d'app iOS provisoire `fr.oris.app` : à fixer avant TestFlight.
- Texte blanc sur Oris Blue (#3B82F6) : contraste 3,7:1, conforme AA seulement en grand
  texte ; le bouton principal est donc en 19 px gras. À revoir avec le design final.
- App iPhone vérifiée par tests unitaires uniquement (pas de capture sur simulateur en M0) ;
  pas encore de tests d'interface.
- Base embarquée (`pixeltable-pgserver`) réservée au développement local.
- CI jamais exécutée avant le premier push de M0 : à confirmer sur GitHub.

