# Essayer Oris sur votre Mac

## 1. Lancer

Double-cliquez **`lancer-oris.command`** dans le dossier du projet. Une fenêtre noire
s'ouvre, annonce quatre étapes, puis le navigateur s'ouvre sur Oris. Laissez la fenêtre
noire ouverte : c'est Oris qui tourne.

Pour tout arrêter : double-cliquez **`arreter-oris.command`**.

## 2. Faire un essai, en trois gestes

1. **Démarrer une consultation** — un seul bouton sur l'accueil.
2. Tapez un nom **inventé** (ou laissez « Patient d'essai »), puis **Démarrer l'écoute**.
3. Cochez « le patient a été informé », puis **Commencer l'écoute**. Le navigateur demande
   l'accès au micro la première fois : acceptez.

Parlez comme en consultation. Quand vous avez fini : **Terminer**. Oris transcrit,
extrait les faits, écrit le compte rendu, puis **supprime le son**.

## 3. Quoi dire pour que l'essai serve à quelque chose

Un essai utile dure deux minutes et contient de quoi piéger Oris :

> « Alors, qu'est-ce qui vous amène ? — J'ai une gêne à droite, surtout au froid, mais je
> n'ai pas mal la nuit. — Sur la 26… pardon, la 27, je note une sensibilité au froid,
> pas de douleur nocturne. Il y a peut-être une fissure, à confirmer. On discute de deux
> options : un composite, ou on surveille. Le patient préfère surveiller pour l'instant.
> On refera le point dans trois mois. »

Vérifiez ensuite dans le compte rendu :

| Ce qui doit apparaître | Ce qui serait un défaut grave |
|---|---|
| la dent **27**, pas la 26 | la 26 écrite quelque part |
| « absence de douleur nocturne » | la douleur nocturne affirmée |
| « suspicion de fissure, non confirmée » | une fissure affirmée |
| « rapporté par le patient » pour la gêne | la gêne écrite comme un constat |
| le composite « discuté », pas « réalisé » | un acte écrit comme fait |

Cliquez sur une phrase du compte rendu : Oris montre le fait qui la justifie et la phrase
que vous avez prononcée.

## 4. Ce qui part à l'extérieur

Pendant l'essai, le **son** part chez Deepgram (transcription) et le **texte** chez Claude
(extraction). Pas l'identité du patient, pas les documents. C'est pour cela que l'essai
se fait avec des situations **inventées** : pas de vrai patient, pas de vrai nom.

## 5. Si ça ne marche pas

| Ce que vous voyez | Quoi faire |
|---|---|
| « Micro refusé par le navigateur » | Autorisez le micro pour `localhost` dans les réglages du navigateur, puis rechargez |
| « Aucune parole n'a été reconnue » | Le micro n'a rien capté : rapprochez-vous, vérifiez l'entrée son du Mac |
| « Le service de transcription n'a pas répondu » | Coupure réseau : l'audio est conservé, relancez le traitement |
| La page ne s'ouvre pas | Relancez `lancer-oris.command`, puis dites-le moi : les journaux sont dans `logs/` |

## 6. Ce que cet essai ne prouve pas

Il montre qu'Oris fonctionne sur **votre voix, dans votre bureau**. Il ne dit rien du
bruit d'un vrai cabinet, ni de la qualité sur une vraie patientèle — c'est le rôle des
séances jouées (`docs/PROTOCOLE_ENREGISTREMENT.md`). Et aucun patient réel ne doit être
enregistré tant que l'hébergement agréé n'est pas en place.
