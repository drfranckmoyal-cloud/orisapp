# Déposer un document d'Oris dans le dossier Veasy du patient

Demande de Franck, 25/11/2026 : « il faut qu'Oris puisse déposer directement le compte
rendu dans le dossier Veasy du patient, il est connecté sur le navigateur ». Franck a
choisi que l'**extension Dental Lens** porte la partie navigateur (et non l'extension
CEMEDIS, qui appartient à son développeur). Même schéma que le dépôt SmileCloud.

## Ce qu'Oris fait

1. Dans la fenêtre d'envoi (site et iPhone), la case **« Dossier Veasy du patient »**.
   Seul un document **validé** part. Décochée d'office tant que le premier vrai dépôt
   n'a pas été vérifié de bout en bout.
2. Oris pose une demande ; il ne touche jamais à Veasy.

## Contrat avec l'extension

Adresse : `https://51-159-130-158.nip.io/mobile` (préfixe), secret partagé en
`Authorization: Bearer <JOURNEE_DEPOT_TOKEN>` — le même que pour SmileCloud et la journée.

### `GET /veasy/demandes`

```json
[{
  "id": "4f…",
  "document_id": "…",
  "nom_fichier": "Oris - compte rendu de consultation.pdf",
  "patient": {"prenom": "Justine", "nom": "DROIT", "date_naissance": "1984-03-02", "veasy_id": ""},
  "demande_le": "2026-11-25T10:00:00+00:00",
  "essais": 0
}]
```

`veasy_id` est vide tant qu'aucun dépôt n'a réussi pour ce patient ; ensuite Oris le
connaît et le donne. `date_naissance` peut être vide (fiche Oris incomplète). Une
demande non servie en 24 h est oubliée.

### `GET /veasy/depot/{id}`

Le PDF à déposer (`application/pdf`), fabriqué à la demande.

### `POST /veasy/depose`

```json
{"id": "4f…", "raison": "", "reessayer": false, "veasy_patient_id": "123456"}
```

- **Réussi** : `raison` vide, et `veasy_patient_id` = le numéro Veasy du dossier où le
  document est entré. Oris le retient sur la fiche (jamais par-dessus un numéro déjà
  connu).
- **Contretemps, rien n'est parti** (page pas prête, session Veasy à reconnecter) :
  `raison` + `reessayer: true` → la demande reste ouverte, revient au passage suivant.
- **Refus** (patient introuvable, homonymes, doute) : `raison` seule → la demande se
  ferme, la raison est montrée au praticien. **En cas de doute sur le patient, ne rien
  déposer.** Un document médical dans le mauvais dossier est la faute à ne jamais faire.

## Ce qu'on sait de Veasy (lu dans l'extension CEMEDIS, sans rien y modifier)

Veasy = `https://patient.visiodent.com`. Un document s'y enregistre par :

```
POST /patient/Patient/Gestion/SaveDocument   (multipart/form-data, cookies de la session)
  patientId  : <idVeasy du patient>
  fileName   : <nom du fichier>
  RemoteFile : <le fichier>
  location   : <classeur de rangement, ex. « Documents »>
→ { "success": true, "idDocument": <id>, "sizeDocument": <octets> }
```

Points à établir par la session Dental Lens, sur la vraie page :

- **Retrouver l'idVeasy** d'un patient à partir du nom, du prénom et de la date de
  naissance (recherche patient de Veasy) — et refuser s'il n'y a pas exactement un
  dossier qui correspond.
- **Le classeur** (`location`) où Franck veut ses comptes rendus : à lui demander.
- **Jeton anti-falsification** éventuel exigé par `SaveDocument` (champ caché de la page).
- **Visibilité** : l'extension CEMEDIS observe ce même `SaveDocument` (dans le monde de la
  page) pour synchroniser les documents vers le système CEMEDIS, et y ajoute un réglage
  « Visible par le patient » (par défaut non). Un envoi fait depuis le monde isolé de
  Dental Lens ne serait **pas** vu par elle. À trancher avec Franck : faut-il que les
  comptes rendus d'Oris remontent aussi chez CEMEDIS ?
- **Vérifier l'arrivée** : `success` + `idDocument` dans la réponse suffisent comme preuve.
