# Audit final de la Master Spec Oris v1.1 → v1.2

Date : 16 septembre 2026

## Résultat

La spec v1.1 est structurellement cohérente et peut servir de base de développement. L’audit automatisé et manuel ciblé a vérifié :

- continuité des sections : 0 à 207 sans doublon ;
- reliquats de l’ancien nom : 0 occurrence ;
- plateforme iPhone native + web cohérente ;
- backend commun cohérent ;
- implantologie/endodontie/Android présents uniquement comme hors-périmètre ou extension future ;
- audio éphémère cohérent avec le Learning Store ;
- apprentissage continu séparé des faits patients ;
- Clinical Encounter Object maintenu comme source de vérité.

## Ajustements apportés en v1.2

1. Identité visuelle Oris désormais figée pour V1.
2. Ajout d’une hiérarchie explicite des sources de vérité.
3. Séparation nette entre infrastructure d’apprentissage à prévoir dès le départ et fonctions MLOps à ne pas développer avant validation du cœur produit.
4. Stratégie fournisseur IA/STT rendue explicitement benchmark-first et interchangeable.
5. Freeze de périmètre avant bascule vers Claude Code.
6. Le point « couleur/logo final » a été remplacé par la seule vectorisation finale de l’asset.

## Risques à surveiller pendant le code

- Ne pas transformer le Learning Engine en second produit avant que l’écoute active fonctionne.
- Ne pas utiliser les documents générés comme source de vérité à la place des faits structurés.
- Ne pas considérer la diarisation comme parfaite : elle doit porter une confiance et pouvoir être corrigée.
- Ne pas écrire de données patient dans logs/analytics/exception tracking.
- Ne pas implémenter un « fallback » qui complète des champs opératoires avec des valeurs habituelles.
- Ne pas faire d’intégration PMS profonde en V1.

## État

**GO pour bascule Claude Code**, sous réserve d’utiliser le Starter Pack et les tests fournis dans ce dossier.
