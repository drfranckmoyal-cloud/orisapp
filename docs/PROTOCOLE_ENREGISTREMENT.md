# Protocole d'enregistrement — consultations jouées

*Pour les praticiens qui acceptent d'enregistrer des consultations jouées afin de mesurer
Oris. Comptez 45 minutes pour une première session de six consultations.*

Rien de ce qui est enregistré ici ne concerne un patient réel. Les situations sont
**jouées**, et c'est indispensable : tant que l'hébergement agréé n'est pas en place, un
vrai patient ne doit jamais être enregistré (`scripts/beta_gate.py` le refuse).

---

## 1. Avant de commencer

1. Remettre la **note d'information** (`docs/consentement/note-information.md`) à chaque
   participant : praticien, personne jouant le patient, assistant(e) s'il y en a un.
2. Faire signer le **consentement** (`docs/consentement/consentement-participant.md`), un
   par participant et par session.
3. Ranger les consentements **hors du dépôt de code**, dans le dossier du cabinet, et
   noter leur référence : elle sera reportée dans le manifeste du jeu d'enregistrements.

**Règle absolue pendant l'enregistrement** : aucun nom de patient réel, aucune date de
naissance, aucun numéro de sécurité sociale, aucun détail permettant de reconnaître
quelqu'un. Utilisez des prénoms inventés.

---

## 2. Matériel et réglages

| Quoi | Recommandé | Pourquoi |
|---|---|---|
| Appareil | iPhone, ou micro USB posé sur le plan de travail | Ce que vous utiliserez vraiment |
| Position | À 50–80 cm des deux interlocuteurs | Les deux voix doivent être audibles |
| Format | Peu importe (m4a, wav, mp3) | Je convertis ensuite en 16 kHz mono |
| Ambiance | **Gardez le bruit habituel** : aspiration, turbine, pas dans le couloir | C'est précisément ce qu'on veut mesurer |

Ne cherchez pas le studio : un enregistrement trop propre ne dit rien du cabinet réel.
Faites en revanche **un essai de 30 secondes** avant la première consultation, et
écoutez-le : si vous ne distinguez pas les deux voix, rapprochez l'appareil.

---

## 3. Ce qu'il faut jouer

Six consultations suffisent pour une première session. Elles doivent couvrir les
situations sur lesquelles Oris est mesuré :

| # | Situation | Ce qui doit absolument y figurer | Durée |
|---|---|---|---|
| 1 | **Consultation esthétique** | une demande du patient, un constat du praticien, deux options discutées dont une écartée, une décision non prise | 3–4 min |
| 2 | **Usures** | l'usure constatée, une étiologie **incertaine** (« peut-être du reflux, à confirmer »), une proposition | 3–4 min |
| 3 | **Composite** (acte réalisé) | dent et face, isolation, adhésif et composite **nommés à voix haute**, finition, contrôle de l'occlusion | 4–5 min |
| 4 | **Facettes** (préparation ou collage) | dents concernées, mock-up ou essayage, empreinte, teinte, provisoires ou matériau de collage | 4–5 min |
| 5 | **Avulsion** | indication, anesthésie, type d'abord, hémostase, sutures, consignes postopératoires | 3–4 min |
| 6 | **Consultation piège** *(la plus utile)* | voir ci-dessous | 2–3 min |

### La consultation piège

C'est celle qui mesure ce qui compte vraiment. Glissez-y, naturellement :

- **une correction de dent** : « sur la 26… pardon, la 27 » ;
- **une négation** : « pas de douleur nocturne » ;
- **une incertitude** : « il y a peut-être une fissure, à confirmer » ;
- **une parole du patient que le praticien ne reprend pas à son compte** : le patient dit
  « je crois que j'ai une carie », le praticien ne le confirme pas ;
- **un acte futur** : « on fera le composite la prochaine fois » — surtout ne pas le faire ;
- **une option refusée** : « les couronnes, je ne veux pas ».

Oris doit écrire « à confirmer », « absence de », « rapporté par le patient », « prévu ».
S'il transforme l'un de ces six points en affirmation, c'est un défaut grave, et c'est
exactement ce que la session sert à débusquer.

---

## 4. Pendant l'enregistrement

- **Parlez comme d'habitude**, y compris en dictant vos actes si c'est votre usage.
- **Nommez les matériaux à voix haute** (marque et teinte) : c'est ce qui alimente le
  compte rendu opératoire.
- Ne répétez pas artificiellement les numéros de dents : on veut la difficulté réelle.
- Si vous vous interrompez, **ne recommencez pas** : les hésitations font partie du test.
- Notez sur une feuille, après chaque consultation, **ce que vous auriez écrit** dans le
  dossier. C'est la référence à laquelle Oris sera comparé.

---

## 5. Après la session

Pour chaque consultation, fournissez :

1. le **fichier audio** ;
2. la **transcription de référence** : qui a dit quoi, dans l'ordre (voir modèle ci-dessous) ;
3. **votre compte rendu**, tel que vous l'auriez rédigé.

### Nommage des fichiers

```
SEANCE-<date>-<numéro>.<extension>
exemple : SEANCE-2026-09-27-03.m4a
```

### Modèle de transcription de référence

Un fichier texte par consultation, une ligne par prise de parole :

```
praticien | Bonjour, qu'est-ce qui vous amène ?
patient   | J'ai une gêne sur le côté droit, surtout au froid.
praticien | Sur la 16, sensibilité au froid rapportée, pas de douleur nocturne.
```

Rôles acceptés : `praticien`, `patient`, `assistant`, `accompagnant`.

---

## 6. Transmission

- **Ne passez pas par courriel non chiffré ni par messagerie grand public.**
- Remettez les fichiers **en main propre** (clé USB, disque) ou par un partage chiffré
  avec mot de passe transmis séparément.
- Une fois les fichiers copiés et vérifiés, **effacez-les de l'appareil d'enregistrement**.

---

## 7. Ce que j'en fais

1. Conversion au format attendu (16 kHz, mono) : `scripts/prepare_recordings.py`.
2. Contrôle du jeu : `scripts/check_dataset.py` — il **refuse** un jeu sans consentement
   documenté et référencé.
3. Mesure : transcription, extraction, comparaison à votre référence et à votre compte
   rendu ; rapport chiffré, par situation.
4. Les enregistrements ne servent qu'à cela, et sont supprimés au plus tard au bout de
   24 mois.

---

## 8. Retrait

Un participant peut retirer son consentement à tout moment, sans justification. Dites-le
moi : je supprime l'enregistrement, et je relance les mesures sans lui.
