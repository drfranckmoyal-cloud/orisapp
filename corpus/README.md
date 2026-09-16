# Corpus synthétique Oris — 100 cas

100 scénarios **entièrement synthétiques**, aucun patient réel.

Répartition : {'aesthetic_consultation': 20, 'tooth_wear_consultation': 20, 'composite_procedure': 20, 'veneer_procedure': 20, 'extraction_procedure': 10, 'adversarial': 10}.

Chaque ligne JSONL contient :
- transcript segmenté avec rôles ;
- faits attendus ;
- plan attendu ;
- procédures attendues ;
- warnings attendus ;
- note clinique attendue.

Usage : tests de schéma, golden tests, non-régression et évaluation comparative des moteurs d’extraction.

Important : ce corpus ne valide pas à lui seul un usage clinique. Il doit ensuite être complété par des consultations simulées par des professionnels puis, seulement dans un cadre gouverné, des évaluations réelles.
