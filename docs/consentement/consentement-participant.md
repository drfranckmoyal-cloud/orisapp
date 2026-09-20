# Consentement à l'enregistrement d'une consultation jouée

*Un exemplaire signé par participant et par session. À conserver hors du dépôt de code,
dans le dossier du cabinet. Ce modèle n'est pas un avis juridique.*

---

**Projet** : Oris — mesure de la qualité d'un assistant de rédaction dentaire
**Responsable du traitement** : ............................................................
**Contact** : ............................................................

## Participant

Nom et prénom : ............................................................

Rôle tenu pendant l'enregistrement (cochez) :
- ☐ praticien
- ☐ personne jouant le patient
- ☐ assistant(e)
- ☐ autre : ....................................

Date de la session : ......... / ......... / .........
Référence de la session (voir protocole) : ....................................

## Ce que je confirme

- ☐ J'ai lu la **note d'information** et j'ai pu poser mes questions.
- ☐ Je comprends que la consultation enregistrée est **jouée** : aucun patient réel n'est
  concerné et **aucune donnée de santé réelle** ne sera prononcée.
- ☐ J'accepte que **ma voix** soit enregistrée et transcrite.
- ☐ J'accepte que ces enregistrements soient envoyés à des **services techniques de
  transcription et d'analyse**, y compris **hors de l'Union européenne** (aujourd'hui
  Deepgram et Anthropic).
- ☐ Je sais que je peux **retirer mon consentement à tout moment**, sans justification, et
  que l'enregistrement sera alors supprimé.
- ☐ Je sais que ces enregistrements ne seront **ni diffusés publiquement, ni vendus**.

## Ce que je refuse (facultatif)

- ☐ Je refuse l'envoi de mes enregistrements hors de l'Union européenne.
  *(Dans ce cas, la session ne peut servir qu'aux mesures effectuées localement.)*
- ☐ Autre restriction : ..................................................................

## Signature

Fait à .................................... le ......... / ......... / .........

Signature du participant : ....................................

Signature du responsable : ....................................

---

**Après signature** : notez la référence de ce document dans le manifeste du jeu
d'enregistrements (champ `consent_reference`), par exemple
`consentements/2026-09-27-seance-03.pdf`. Le contrôle `scripts/check_dataset.py` refuse
un jeu non synthétique sans cette référence.
