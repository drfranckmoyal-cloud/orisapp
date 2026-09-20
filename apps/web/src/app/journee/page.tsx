import { Carte, EnTetePage, EtatVide, Pastille } from "@/components/ui";

/** Votre journée — chantier à venir.
 *
 * L'écran existe parce qu'il change le départ de tout le reste : si la liste des
 * patients du jour arrive de l'agenda, les dossiers n'ont plus à être créés à la
 * main et l'écoute démarre d'un geste. Mieux vaut que la place soit prise, et que
 * ce qui manque soit écrit.
 */
export default function JourneePage() {
  return (
    <div className="page">
      <EnTetePage
        surTitre="Chantier à venir"
        titre="Votre journée"
        action={<Pastille ton="attention">non construit</Pastille>}
      />

      <Carte titre="Ce que cet écran fera">
        <EtatVide titre="Rien à afficher pour l’instant">
          L’agenda n’est pas encore relié à Oris.
        </EtatVide>
        <ul className="liste-simple">
          <li>
            <strong>Récupérer les rendez-vous du jour depuis Doctolib</strong> : heure, motif,
            praticien, et l’état civil du patient.
          </li>
          <li>
            <strong>Créer les dossiers automatiquement</strong> à partir de ces données —
            nom, prénom, date de naissance, courriel — au lieu de les saisir un par un.
          </li>
          <li>
            <strong>Démarrer l’écoute d’un geste</strong> depuis la ligne du rendez-vous :
            le patient est déjà choisi, il n’y a plus qu’à commencer.
          </li>
          <li>
            Voir d’un coup d’œil, en fin de journée, <strong>quels rendez-vous ont leur
            compte rendu</strong> et lesquels attendent encore.
          </li>
        </ul>
      </Carte>

      <Carte titre="Ce qu’il faudra régler avant">
        <ul className="liste-simple">
          <li>
            <strong>L’accès à Doctolib.</strong> Une interface d’échange existe pour les
            éditeurs partenaires ; il faut la demander, et savoir ce qu’elle donne
            réellement. Sans elle, il ne reste que des exports manuels.
          </li>
          <li>
            <strong>Le cadre juridique.</strong> Importer l’état civil d’un patient depuis
            un agenda, c’est traiter des données de santé : cela suppose l’hébergement
            agréé et la base légale, pas seulement une clé d’accès.
          </li>
          <li>
            <strong>Les doublons.</strong> Un patient déjà connu d’Oris ne doit pas être
            créé une seconde fois parce que l’agenda l’orthographie autrement. C’est à
            cela que sert l’<strong>identifiant externe</strong> de la fiche patient :
            aujourd’hui il ne sert à rien, il deviendra le lien avec l’agenda. Il se
            saisit à la création et n’encombre pas la fiche.
          </li>
        </ul>
        <p className="muted" style={{ margin: 0 }}>
          Rien de tout cela n’est un obstacle — mais aucun ne se contourne, et le premier
          conditionne les autres.
        </p>
      </Carte>
    </div>
  );
}
