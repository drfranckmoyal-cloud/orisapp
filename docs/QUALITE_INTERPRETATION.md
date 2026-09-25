# Obtenir l'interprétation la plus juste d'une consultation

*État de l'art et plan d'action pour Oris — 26 septembre 2026. Sources en fin de document.*

---

## 1. Ce que la recherche mesure aujourd'hui

Les chiffres publiés en 2025–2026 sur les « scribes ambiants » (les produits qui
écoutent la consultation et rédigent la note) donnent la mesure du problème :

- **Hallucinations** — affirmations que personne n'a prononcées : détectées dans **31 %
  des notes produites par IA**, contre 20 % dans les notes de référence écrites par des
  médecins (étude comparative, p = 0,01).
- **Omissions** — l'inverse, et le vrai danger : sur cinq plateformes de scribe évaluées
  sur des consultations simulées, **26,3 % en moyenne des éléments cliniques clés étaient
  omis ou mal captés**.
- **Reconnaissance vocale** — le taux d'erreur mot (WER) **double** quand on passe d'un
  enregistrement propre à un environnement bruyant à plusieurs locuteurs, ce qui est
  exactement le fauteuil dentaire. Un travail francophone sur Whisper Large-v2 adapté à
  la radiologie atteint **17,1 % de WER en français médical** — c'est-à-dire qu'un mot
  sur six est faux avant même que le modèle de rédaction ne commence son travail.
- **Prudence excessive** — les brouillons d'IA contiennent **nettement plus de formules
  d'incertitude** (« semble », « pourrait ») que les notes finales : les praticiens les
  suppriment systématiquement à la relecture. Un brouillon trop prudent coûte du temps
  de correction.
- **Les juges automatiques sont aveugles à l'absence** — un LLM chargé d'évaluer une note
  « vérifie la présence, pas l'absence » : il repère bien ce qui est écrit à tort, il
  rate ce qui manque. Or l'omission est l'erreur clinique la plus grave.
- **Les grilles d'évaluation globales ne suffisent pas** — la PDQI-9, référence
  historique pour noter la qualité d'une note, donne des désaccords importants entre
  relecteurs, y compris sur la définition d'une hallucination.

**Conclusion à retenir : la bataille de la qualité ne se gagne pas sur « quel modèle »,
elle se gagne sur la chaîne — reconnaissance vocale, extraction contrainte, vérification
de ce qui manque, et mesure continue.**

---

## 2. Ce qu'Oris fait déjà bien

Ce n'est pas de l'autosatisfaction : il faut savoir ce qui est acquis pour ne pas le
refaire.

| Technique de l'état de l'art | Oris | Où |
|---|---|---|
| Sortie contrainte par un schéma (structured output / tool schema) | ● le modèle ne peut répondre que par l'outil `enregistrer_faits_cliniques`, schéma issu des contrats | `llm/schema_bundle.py` |
| Preuve obligatoire par fait (evidence spans) | ● chaque fait cite `evidence_segment_ids`, uniquement des segments fournis | `llm/prompt.py` |
| Préservation de la négation, de la temporalité, de l'incertitude, du rôle du locuteur | ● règles explicites du prompt + résolveur | `llm/prompt.py`, `domain/resolver.py` |
| Vérification déterministe après extraction | ● FDI valide, cohérence des statuts, corrections, doublons | `domain/resolver.py` |
| Deuxième passe corrective avec l'erreur en retour | ● 3 essais maximum, l'erreur exacte est renvoyée au modèle | `llm/anthropic_extraction.py` |
| Refus plutôt que réparation silencieuse | ● une sortie non conforme est rejetée, jamais corrigée en douce | idem |
| Vocabulaire métier poussé à la reconnaissance vocale | ● `keyterm` chez Deepgram, `phraseList` chez Azure, glossaire dentaire + glossaire du praticien | `stt/common.py`, `stt/deepgram.py`, `stt/azure_speech.py` |
| Diarisation (qui parle) | ◐ activée chez les deux fournisseurs, mais les rôles ne sont pas encore attribués finement | `stt/*.py` |
| Documents = projections des faits, jamais du texte libre | ● | `services/documents.py` |
| Validateur factuel à la rédaction | ● chaque énoncé doit s'appuyer sur un identifiant de fait | `FactualValidator` |
| Corpus de cas et non-régression | ◐ 100 consultations synthétiques, cas critiques, banc STT | `corpus/`, `evals/`, `scripts/stt_benchmark.py` |
| **Détection des omissions** | ○ **rien** | — |
| **Auto-cohérence (plusieurs tirages)** | ○ | — |
| **Contexte du patient (antériorité)** | ○ | — |
| **Preuve montrée au praticien** | ○ (la donnée existe, l'écran non) | — |
| **Mesure chiffrée de la qualité d'extraction** | ○ pas de score fait-par-fait | — |

**En clair : Oris est déjà du bon côté sur la non-invention. Il est nu sur l'omission et
sur la mesure.**

---

## 3. Les neuf leviers, du plus rentable au plus lourd

### Levier 1 — La passe de complétude : chercher ce qui manque *(le plus rentable)*

C'est le résultat le plus directement applicable de la recherche 2026 : un modèle ne
détecte une omission **que si on lui demande explicitement ce qui manque**, liste en
main. Demander « cette note est-elle complète ? » ne marche pas ; demander « parmi ces
éléments, lesquels sont absents ? » marche.

Recette :

1. Après l'extraction, une **seconde passe** reçoit la transcription **et** la liste des
   faits extraits, avec une seule question : *« quelles informations cliniques présentes
   dans la transcription ne figurent dans aucun fait ? »*
2. Chaque manque signalé doit citer son segment — sinon il est ignoré.
3. Les manques deviennent des **faits candidats**, soumis aux mêmes règles
   déterministes, et signalés au praticien comme « à confirmer » plutôt qu'insérés
   silencieusement.
4. Une **check-list par type de consultation** (motif, antécédents pertinents, examen,
   dents concernées, actes réalisés, décision, suite prévue) sert de grille d'absence :
   les éléments de la check-list jamais abordés sont affichés comme **non documentés**,
   pas inventés.

Gain attendu : c'est le seul levier qui attaque les 26 % d'omissions.
Effort : moyen. Un appel de plus par consultation, un écran de plus.

### Levier 2 — Rendre la preuve visible et audible

Oris impose déjà la citation du segment source. Abridge en a fait son argument n°1 sous
le nom *Linked Evidence* : cliquer une phrase du compte rendu montre le passage de la
transcription et permet de réécouter l'audio.

Chez nous : la donnée est là (`evidence_segment_ids`, horodatage des segments). Il
manque l'écran — côté site **et** côté iPhone (règle de parité). L'audio n'est conservé
que le temps du traitement : on peut donc offrir la transcription au clic tout de suite,
et l'audio seulement si la politique de conservation évolue.

Gain : double. Le praticien relit **plus vite** (il vérifie au lieu de relire tout), et
c'est un argument commercial qu'aucun concurrent français n'affiche.
Effort : faible côté serveur, moyen côté écrans.

### Levier 3 — L'auto-cohérence sur les données à risque

Un modèle ne rend pas deux fois la même sortie. Sur les données où une erreur se paie
cher — **numéro de dent, surface, matériau, posologie, chiffre** — on peut extraire
**trois fois** et comparer :

- valeur identique sur les trois → confiance haute, rien à signaler ;
- valeur divergente → le fait est marqué **incertain** et remonté en tête de relecture.

La littérature montre des gains nets par auto-critique itérative (F1 de 0,83 → 0,91 sur
du compte rendu structuré, exactitude 0,68 → 0,83 sur de la stadification).

Variante moins coûteuse : ne relancer que sur les faits dont la confiance déclarée par
le modèle est basse, ou qui portent un numéro de dent.

Effort : faible (le code d'extraction est déjà idempotent et retente déjà). Coût : deux
appels de plus, uniquement quand c'est utile.

### Levier 4 — Gagner en amont, sur la reconnaissance vocale

Tout ce qui est mal entendu est définitivement perdu. Trois actions, par ordre d'effet :

1. **Enrichir le glossaire dentaire** poussé en `keyterm` / `phraseList`. La limite
   actuelle est de 50 termes (`stt/common.py`) : c'est peu. La recherche prévient qu'une
   liste trop longue de termes rares **dégrade** la reconnaissance (les mots non
   prononcés deviennent des distracteurs) — donc : glossaire **contextuel**, pas
   exhaustif. Les termes du praticien d'abord, puis les termes de l'acte prévu, puis le
   fonds dentaire commun.
2. **Attribuer les rôles**, pas seulement les locuteurs : la diarisation dit « locuteur
   1 / locuteur 2 », pas « praticien / patient / assistante ». Une règle simple (qui
   parle le plus, qui emploie le vocabulaire technique, qui a lancé l'écoute) suffit à
   fiabiliser le `speaker_role`, dont dépendent les statuts `patient_reported` vs
   `observed` — invariant clinique n°5.
3. **Comparer deux moteurs sur le corpus** (le banc existe déjà :
   `scripts/stt_benchmark.py`, 46+ fichiers synthétiques) et mesurer le WER **sur le
   vocabulaire dentaire seul**, pas sur tous les mots : une erreur sur « donc » ne coûte
   rien, une erreur sur « 26 » coûte tout.

### Levier 5 — Donner le contexte du patient, en lecture seule

Les plateformes 2026 résument l'historique avant la consultation. Chez Oris, le modèle
ne voit aujourd'hui **que les segments du jour**. Lui fournir le plan de traitement en
cours et le dernier compte rendu permettrait de comprendre « on fait la deuxième
facette » ou « comme prévu ».

**Garde-fou absolu :** ce contexte est fourni comme **contexte de compréhension, jamais
comme source de faits**. Un fait ne peut citer qu'un segment du jour. Le prompt doit le
dire explicitement, et le résolveur le vérifier — sinon on recrée exactement
l'hallucination que l'architecture interdit.

### Levier 6 — Calibrer le ton sur les documents validés

Les brouillons d'IA sont trop prudents ; les praticiens suppriment ces formules. Deux
actions :

- interdire dans le prompt de rédaction les tournures d'incertitude **rédactionnelle**
  (« semble », « il apparaît que ») tout en conservant l'incertitude **clinique** quand
  elle a été exprimée (« le patient n'est pas sûr de la date ») — ce sont deux choses
  différentes et il ne faut pas les confondre ;
- alimenter la rédaction avec **trois à cinq extraits de documents validés du
  praticien** comme exemples de style. C'est déjà l'esprit du module d'apprentissage :
  le style, jamais le contenu.

### Levier 7 — Mesurer, sinon rien de ce qui précède n'est prouvable

Sans mesure, chaque changement de prompt est un pari. Il faut un **banc d'essai
d'extraction** à côté du banc STT existant :

- **Corpus de référence** : les 100 consultations synthétiques existantes, annotées
  main à main avec les faits attendus (dents, statuts, temporalité, rôle).
- **Métriques par fait, pas par note** : précision et rappel des faits ; taux
  d'hallucination (fait sans appui réel) ; **taux d'omission** (fait attendu absent) ;
  exactitude des numéros de dents ; exactitude des statuts (proposé / accepté / réalisé).
- **Grilles par cas plutôt que note globale** : la recherche 2026 montre que des
  rubriques spécifiques au cas donnent un bien meilleur accord entre juges que les
  échelles générales type PDQI-9 (validé sur 823 consultations).
- **Juge automatique en deux temps** : une passe « ce qui est écrit est-il appuyé ? » et
  une passe « ce qui est attendu est-il présent ? », avec la check-list — sans quoi le
  juge est aveugle à l'absence (levier 1).
- **Non-régression** : aucun changement de `PROMPT_VERSION` ne part sans le banc au vert.
  Le versionnement est déjà en place (`extraction-fr-5`, `redaction-fr-3`) ; il manque le
  score.

### Levier 8 — Vocabulaire et valeurs contrôlées

Oris fournit déjà au modèle la liste des concepts connus avec leur sens, et les
emplacements attendus par acte. C'est la bonne approche (schema-grounded extraction).
Deux extensions possibles : rattacher les concepts à une nomenclature reconnue (FDI est
déjà là ; CCAM pour les actes serait la suite naturelle, et ouvrirait le devis), et
refuser tout concept inventé hors d'une liste de secours tracée.

### Levier 9 — Le modèle lui-même, en dernier

Changer de modèle est le levier le plus visible et le moins rentable **une fois** que la
chaîne est bonne. À garder cependant : un banc qui compare, à chaîne identique, le
modèle actuel et un ou deux concurrents sur le corpus annoté. Le résultat ne vaut que
mesuré sur *nos* cas, jamais sur les chiffres marketing d'un éditeur.

---

## 4. Ordre de marche proposé

| Lot | Contenu | Effet |
|---|---|---|
| **A** | Levier 7 (banc d'extraction + corpus annoté + métriques) | Sans lui, rien n'est mesurable. C'est le socle. |
| **B** | Levier 1 (passe de complétude) + levier 3 (auto-cohérence sur dents et chiffres) | Attaque directement les deux erreurs graves : omission et numéro de dent faux. |
| **C** | Levier 2 (preuve visible, site + iPhone) | Relecture plus rapide, argument commercial unique. |
| **D** | Levier 4 (glossaire contextuel, rôles des locuteurs) et levier 6 (ton) | Moins d'erreurs en amont, moins de corrections en aval. |
| **E** | Levier 5 (contexte patient) puis levier 8 (CCAM) | Ouvre le devis et la continuité des soins. |

Chaque lot respecte la règle de parité site ↔ iPhone (D028) et les dix invariants de
sécurité clinique du `CLAUDE.md` du dépôt. Aucun de ces leviers n'autorise Oris à
produire un fait que personne n'a prononcé.

---

## Sources

- [Evaluating the Quality and Safety of Ambient Digital Scribe Platforms Using Simulated Ambulatory Encounters (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12605248/) — 26,3 % d'éléments omis ou erronés sur cinq plateformes
- [Assessing the quality of AI-generated clinical notes: validated evaluation of an LLM ambient scribe (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12586549/) — hallucinations 31 % vs 20 %, PDQI-9 modifiée
- [LLM Judges Verify Presence, Not Absence: Omission Blindness in AI Clinical Notes and What Recovers It (arXiv 2608.31016)](https://arxiv.org/pdf/2608.31016)
- [Case-Specific Rubrics for Clinical AI Evaluation: Methodology, Validation, and LLM-Clinician Agreement Across 823 Encounters (arXiv 2604.24710)](https://arxiv.org/pdf/2604.24710)
- [Examine Clinicians' Modification of Hedging Language in Ambient AI Documentation (arXiv 2606.00018)](https://arxiv.org/pdf/2606.00018)
- [Deep reflective reasoning in interdependence constrained structured data extraction from clinical notes (arXiv 2603.20435)](https://arxiv.org/pdf/2603.20435) — F1 0,828 → 0,911
- [Retrieval-Augmented LLMs for Schema-Constrained Clinical Information Extraction (arXiv 2605.15467)](https://arxiv.org/abs/2605.15467)
- [Mitigating Hallucinations in Healthcare LLMs with Granular Fact-Checking (arXiv 2512.16189)](https://arxiv.org/html/2512.16189v1) — vérification proposition par proposition
- [Reducing Hallucinations in Medical AI Through Citation Enforced Prompting in RAG Systems (MDPI)](https://www.mdpi.com/2076-3417/16/6/3013)
- [Benchmarking and datasets for ambient clinical documentation: a scoping review (medRxiv)](https://www.medrxiv.org/content/10.1101/2025.01.29.25320859v1.full)
- [Medical voice recognition: how AI solves terminology problems (AssemblyAI)](https://www.assemblyai.com/blog/medical-voice-recognition) — limites du boosting de mots-clés
- [How to benchmark medical speech recognition accuracy (Deepgram)](https://deepgram.com/learn/benchmark-medical-speech-recognition-accuracy-production)
- [French ASR in healthcare — Whisper Large-v2 adapté, WER 17,1 % (PMC)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11083196/)
- [ASR performance for digital scribes: general-purpose vs specialized models (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10148344/)
- [Abridge — Verify a Note With Linked Evidence](https://support.abridge.com/hc/en-us/articles/30235128433811-Verify-a-Note-With-Linked-Evidence)
