# Changelog

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
