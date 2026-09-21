# Récupérer les photos SmileCloud dans le dossier patient

*Cadrage arrêté avec Franck le 21 septembre 2026. Aucun code écrit à cette date :
ce document dit quoi construire, dans quel ordre, et ce qu'il ne faut pas casser.*

---

## Ce que ça doit faire

Dans un dossier patient, onglet **« Documentation / Pièces jointes »**, un bouton
**« Récupération SmileCloud »**. Franck clique, voit les galeries de ce patient avec
leurs dates, coche celles qu'il veut, et les fichiers arrivent dans le dossier Oris.

C'est tout. Le reste de ce document existe pour que ce geste-là reste simple.

### Pourquoi l'onglet change de nom

SmileCloud appelle « Documentation » l'onglet d'où viennent ces fichiers. Le même mot
des deux côtés évite à Franck de traduire dans sa tête. L'ancien nom reste en second :
**« Documentation / Pièces jointes »**.

---

## 1. Le lien patient ↔ dossier SmileCloud

C'est le vrai sujet. Récupérer des photos suppose de savoir **quel dossier SmileCloud**
est celui de ce patient.

### Un champ dédié, surtout pas `external_id`

`Patient.external_id` existe déjà, mais il porte **le numéro de dossier du cabinet** :
saisi à la main, affiché en pastille, cherchable depuis la liste des patients. S'en
servir pour SmileCloud ferait perdre l'un des deux.

**Fait le 21/09/2026** : `Patient.smilecloud_case_id` (migration `0012`), nullable,
jamais journalisé, posé et retiré par `PATCH /patients/{id}`. Il porte l'identifiant lu
dans l'adresse `…/case/<uuid>/documentation/…`.

### Comment il se pose

Une fois par patient, pas à chaque récupération. Reprendre exactement la discipline
déjà éprouvée dans Dental Lens (voir §2 de `docs/RECUPERATION-SMILECLOUD.md` du dépôt
`smilecloud-photos`) :

- proposition automatique par **ressemblance de nom, avec son pourcentage** — tolérante
  à la casse, aux accents, à l'inversion nom/prénom ;
- **au-dessus du seuil de certitude**, le lien est proposé comme acquis ;
- **en cas de doute**, Oris demande et ne devine pas : orthographe différente, prénom
  composé, homonyme ;
- **recherche manuelle** en dernier recours, et **la réponse de Franck se retient** —
  « c'est le même dossier » ou « aucun de ceux-là » ne doit plus jamais être redemandé.

### D'où vient la liste des dossiers SmileCloud

De l'extension Chrome, qui la livre à Oris comme elle lui livre déjà la journée
Doctolib. **Oris fait lui-même son rapprochement** : il ne demande rien à Dental Lens,
et le lien, une fois posé, est rangé chez lui. Après ça, le dossier du patient se
suffit à lui-même.

---

## 2. Ce qu'on rapatrie

### Les galeries, cochées une par une

SmileCloud range les fichiers en **galeries datées**. La récupération les affiche avec
leur date et leur nombre de fichiers, et Franck coche. **Jamais « tout aspirer »** : un
patient complet pèse environ 1 Go.

### Photos, radios, scans 3D, PDF — pas de vidéos

Arbitrage de Franck : pas de vidéos, pas de CBCT. Deux raisons qui se rejoignent — une
vidéo n'a rien à faire dans un compte rendu opératoire, et elle dépasserait de toute
façon la limite de 80 Mo par fichier.

### Ce qui ne passe pas se dit

Oris refuse les formats qu'il ne sait pas rouvrir et les fichiers trop lourds. Ces
refus **s'affichent** : « 3 fichiers non repris : format non reconnu ». Un fichier
écarté en silence est un fichier qu'on croit avoir.

---

## 3. Comment les fichiers arrivent

**Par la porte qui existe déjà.** `POST /patients/{id}/attachments` sait recevoir des
fichiers, les ranger dans le magasin, calculer leur empreinte et **refuser les
doublons**. Un cliché déjà importé à la main ne se rangera pas deux fois. Rien à
construire de ce côté.

Ce qui est nouveau : c'est l'extension Chrome qui pousse ces fichiers, en les lisant
directement chez SmileCloud. **Rien ne transite par le disque** — pas d'archive, pas de
fichier dans les téléchargements, aucune photo de patient posée dans un dossier
temporaire. Vérifié le 21/09/2026 : l'original arrive entier (932 ko, 2160 × 3246).

Conséquences pour l'écran : la récupération **prend du temps** et se fait fichier par
fichier. Donc un état « récupération en cours », les pièces qui apparaissent au fur et
à mesure, et aucune attente bloquante. Même discipline que la lecture de l'agenda.

### La dépendance, et sa limite

Règle arrêtée avec Franck : *on ne dépend jamais d'une autre application pour exister,
on peut en dépendre pour un geste.*

L'onglet marche parfaitement sans rien : Franck y dépose ses fichiers à la main comme
aujourd'hui. Le bouton de récupération, lui, a besoin de l'extension Chrome — pas de
Dental Lens. **Si Dental Lens est éteint, le bouton marche quand même.**

---

## 4. Ce qui ne change pas

- **Oris ne lit pas les pièces jointes** (§55). Les photos venues de SmileCloud
  accompagnent le dossier ; elles ne nourrissent aucun compte rendu, aucun fait
  clinique n'en sort. La récupération ne doit pas devenir « Oris analyse vos photos ».
- **Aucun patient créé par ce chemin.** Le lien se pose sur un dossier qui existe.
- **Rien dans les journaux techniques** : ni nom de patient, ni nom de galerie, ni
  identifiant de dossier SmileCloud. On ne compte que des fichiers.

---

## 5. Deux préalables, à faire avant

### a) Sortir les pièces jointes du dossier `Caches` — **fait le 21/09/2026**

`Settings.attachment_dir` pointait sur `~/Library/Caches/Oris/attachments` : le dossier
que macOS s'autorise à **vider** quand il manque de place, et qui n'est pas sauvegardé
comme le reste. Sans conséquence tant qu'il n'y a que des fichiers d'essai ; le jour où
on y verse les photos des patients, elles peuvent disparaître sans prévenir.

`attachment_dir` vaut désormais `~/Library/Application Support/Oris/attachments`, là où
Oris range déjà les journées. Les trois fichiers d'essai présents ont été déplacés et
chacun revérifié par son empreinte avant que l'original ne soit retiré.

Au passage : `audio_temp_dir` est dans `Caches` aussi — et là c'est justifié, l'audio
est éphémère par décision (D010). On n'y touche pas.

### b) Partager la reconnaissance de noms — **fait le 21/09/2026**

Le même problème est résolu deux fois : une version à pourcentages dans Dental Lens,
une version simple dans Oris (`_cle()` de `api/journee.py`, qui met à plat casse et
accents mais ne sait pas rapprocher « Paul » de « Paule »). Les deux sont en Python.

La version de Dental Lens est la bonne. Elle est transposée dans
`services/rapprochement.py`, avec ses deux seuils, et l'écran « Votre journée » s'en
sert déjà. Le lien SmileCloud s'en servira au troisième pas.

---

## 6. Ce qui reste ouvert

- **L'autorisation de la route qui reçoit les fichiers** : reprendre la règle de
  `/journee/depot` — appels locaux uniquement, jeton facultatif en en-tête.
- **Le cadre juridique** : ce document suppose Oris sur le Mac du cabinet (D84). **À
  re-trancher avant la première mise en ligne**, comme pour la journée Doctolib.

---

## L'ordre

1. ~~Le déménagement hors de `Caches`.~~ **Fait.**
2. ~~Le champ « dossier SmileCloud » et la reconnaissance de noms partagée.~~ **Fait** —
   mais rien n'est encore visible dans l'application : choisir un dossier suppose la
   liste que l'extension livrera, donc le pas suivant.
3. L'onglet renommé et la récupération.

Les deux premiers sont petits. Le troisième est le vrai morceau, et il sera beaucoup
plus simple une fois les deux autres posés.
