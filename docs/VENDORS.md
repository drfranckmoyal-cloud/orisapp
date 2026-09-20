# Flux de données vers les fournisseurs extérieurs

Ce tableau doit être rempli **avant** tout patient réel (docs/SECURITY.md, spec §66).
Tant qu'une ligne reste vide, le fournisseur est « non revu » et la porte d'entrée en
bêta (`scripts/beta_gate.py`) refuse la mise en service.

Ce document décrit ce qu'Oris envoie. Il ne remplace ni un contrat, ni un DPA, ni un avis
juridique.

## Deepgram — transcription

| Question | Réponse |
|---|---|
| Finalité | Transformer le son de la consultation en texte |
| Données envoyées | Audio de la consultation (PCM 16 kHz), glossaire de termes dentaires |
| Données **non** envoyées | Identité du patient, dossier clinique, documents |
| Région de traitement | à documenter |
| Conservation | à documenter |
| Usage pour l'entraînement | à documenter (doit être exclu) |
| Sous-traitants | à documenter |
| Contrat / DPA | à documenter |
| Pertinence HDS | à documenter |
| Comportement en cas de panne | Transcription refusée, audio conservé, consultation relançable |
| Suppression | à documenter |

## Anthropic (Claude) — extraction clinique

| Question | Réponse |
|---|---|
| Finalité | Transformer le transcript en faits cliniques structurés |
| Données envoyées | Transcript de la consultation, vocabulaire d'Oris, dictionnaire du praticien |
| Données **non** envoyées | Identité du patient, audio, documents déjà rédigés |
| Région de traitement | à documenter |
| Conservation | à documenter |
| Usage pour l'entraînement | à documenter (doit être exclu) |
| Sous-traitants | à documenter |
| Contrat / DPA | à documenter |
| Pertinence HDS | à documenter |
| Comportement en cas de panne | Extraction refusée, consultation en échec explicite, relançable |
| Suppression | à documenter |

## Azure AI Speech — transcription (comparaison)

| Question | Réponse |
|---|---|
| Finalité | Comparer la qualité de transcription à Deepgram |
| Données envoyées | Audio de consultations synthétiques uniquement, à ce stade |
| Région de traitement | à documenter |
| Conservation | à documenter |
| Usage pour l'entraînement | à documenter (doit être exclu) |
| Sous-traitants | à documenter |
| Contrat / DPA | à documenter |
| Pertinence HDS | à documenter |
| Suppression | à documenter |

## Ce qui ne sort jamais d'Oris

- l'identité du patient (nom, date de naissance, identifiant) ;
- les documents rédigés ;
- le journal d'audit ;
- les corrections et le dictionnaire du praticien (sauf le dictionnaire, transmis comme
  simple liste de mots, sans lien avec un patient).
