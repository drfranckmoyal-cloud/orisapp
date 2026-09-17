# Banc d'essai transcription — oris-synthetic-tts-v1 v1

3 enregistrement(s), langue fr-FR.

> **Données synthétiques (voix de synthèse macOS).** Ce banc valide la chaîne de mesure et donne une première tendance ; il **ne suffit pas** pour choisir un fournisseur : il faut des consultations simulées par des professionnels, en cabinet.

## Résultats

| Mesure | deepgram (nova-3-prerecorded) |
|---|---|
| Numéros de dent exacts | 100.0 % |
| Numéros de dent inventés ou faux | 0 |
| Termes dentaires / marques retrouvés | 100.0 % |
| Négations conservées | 100.0 % |
| Locuteurs bien séparés | 72.9 % |
| Rôles praticien / patient bien attribués | 72.9 % |
| Taux d'erreur de mots (WER) | 3.2 % |
| Requêtes réussies | 100.0 % |
| Délai de transcription finale, médian (s) | 6.62 |
| Délai de transcription finale, 95e centile (s) | 6.81 |
| Délai / durée audio, 95e centile | 0.24 |
| Gain du glossaire sur les termes | 0.0 % |
| Gain du glossaire sur les dents | 0.0 % |
| Gain du glossaire sur le WER | 0.4 % |
| Score pondéré | 94.3 % |
| Part de la pondération mesurée | 95.0 % |

## Conformité (préalable, pas un bonus)

- deepgram : conformité HDS / contrat **non évaluée**.

## Erreurs critiques

- deepgram : 0 — aucune

## Méthode

- Mêmes fichiers audio pour chaque fournisseur ; textes normalisés (minuscules, ponctuation retirée, numéros de dent en chiffres) avant comparaison.
- Numéros de dent et négations : comptés justes seulement s'ils sont alignés au même endroit que dans la référence.
- Locuteurs : meilleure correspondance entre étiquettes du fournisseur et locuteurs réels, au temps de parole.
- Score pondéré : tooth_number_accuracy 25 %, critical_term_recall 15 %, negation_preservation 15 %, speaker_accuracy 10 %, wer_score 10 %, latency_score 10 %, customization_score 5 %, reliability 5 %, cost_score 5 %. Une mesure absente (tarif non renseigné, direct non testé) est retirée de la pondération ; la part mesurée est indiquée.
- Latence : direct = 1 − p95/3 s ; sinon 1 − (délai/durée audio). Coût : 1 − coût/10 USD.

Aucun fournisseur n'est choisi par ce rapport (décision D020).
