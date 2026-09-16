# START HERE — Oris

Tu prends en charge Oris, un assistant de documentation clinique dentaire français.

## Mission immédiate

Construire un vertical slice de bout en bout, sans audio réel ni fournisseur IA réel :

`Patient → Encounter → Synthetic Transcript → Clinical Facts → Clinical Encounter → Treatment Plan → Documents → Review → Validation → LearningEvent`

## Ce que tu ne fais PAS dans le premier lot

- pas de SDK STT réel ;
- pas de LLM réel ;
- pas de fine-tuning ;
- pas d’intégration logiciel dentaire ;
- pas d’implantologie ;
- pas de facturation/agenda/CCAM ;
- pas de dashboard complexe.

## Definition of Done du premier vertical slice

- backend démarre localement ;
- migrations fonctionnent ;
- schémas JSON valident ;
- web affiche un patient et une consultation synthétique ;
- iOS affiche le même encounter via API ;
- génération mock produit CR + plan ;
- correction 26→27 met à jour l’objet puis régénère les sorties ;
- LearningEvent est créé ;
- tests critiques A–J passent ;
- aucune donnée clinique dans les logs.

Ensuite seulement : capture micro et bench STT.
