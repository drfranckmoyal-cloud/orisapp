# Prompts de bascule vers Claude Code

## Prompt 0 — initialisation

Lis dans cet ordre START_HERE.md, CLAUDE.md, ORIS_MASTER_SPEC_V1_2.md, docs/DECISIONS.md, schemas/README.md et docs/IMPLEMENTATION_PLAN.md. Ne code rien avant d’avoir produit un court `docs/IMPLEMENTATION_LOG.md` décrivant l’architecture retenue et les fichiers du Milestone M0. Ne branche aucun fournisseur IA réel. Implémente uniquement M0, exécute tests/lint/typecheck, puis arrête-toi avec un résumé factuel de ce qui fonctionne et de ce qui manque.

## Prompt 1 — vertical slice

Implémente M1 strictement. Utilise MockProviders et les fixtures synthétiques. Le flux doit aller de Patient à LearningEvent. La correction 26→27 doit modifier le Clinical Encounter Object, rendre les documents précédents obsolètes et régénérer. Ajoute les tests critiques avant de déclarer M1 terminé.

## Prompt 2 — audio web

Implémente M2 sans modifier les règles cliniques. Ajoute permissions micro, chunk IDs, séquence, checksum, retry, pause/reprise et reprise après coupure courte. N’envoie encore aucun audio à un STT externe : utilise un sink local/mock et teste les états.

## Prompt 3 — audio iOS

Implémente M3 avec APIs audio natives. Teste interruption, route change, background behavior permis, réseau coupé et reprise. Ne masque jamais un gap audio.

## Prompt 4 — benchmark STT

Implémente l’interface SpeechToTextProvider et deux adapters candidats, configurables. Construis un harness qui calcule les métriques définies dans docs/TECHNICAL_BENCHMARK.md. Ne choisis pas encore de provider par défaut en production.

## Prompt 5 — Clinical Engine

Implémente M5. Le provider doit produire un JSON strict conforme aux schemas. Ajoute le resolver déterministe et le factual validator. Aucun document n’est généré directement depuis le transcript. Fais passer le corpus synthétique et rends un rapport d’évaluation versionné.

## Prompt 6 — UI clinique

Implémente M6 conformément à docs/DESIGN_SYSTEM.md. L’interface est en français. Pas de dashboard analytics. Priorité aux états micro/réseau, warnings, provenance et validation.

## Prompt 7 — opératoire

Implémente M7 sans champs par défaut cliniques. Les templates définissent des emplacements attendus, jamais des actes supposés. Ajoute un test prouvant qu’un matériau fréquemment utilisé n’est pas injecté s’il n’est pas prononcé.

## Prompt 8 — apprentissage

Implémente M8 puis M9. Toute correction structurée émet LearningEvent. Les préférences sont locales, inspectables et réversibles. Ne crée aucun entraînement automatique en production.

## Prompt de revue périodique

Avant de poursuivre, audite le repo contre CLAUDE.md, DECISIONS.md et ACCEPTANCE_CRITERIA.md. Liste uniquement : divergences, dette technique dangereuse, tests manquants, risques PHI/logging et expansion de périmètre. Corrige les P0 avant toute nouvelle feature.
