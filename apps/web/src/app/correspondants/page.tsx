import { Carte, EnTetePage, EtatVide } from "@/components/ui";

/** Correspondants — chantier à venir.
 *
 * L'écran existe parce que le rattachement d'un patient à ses correspondants
 * change la fiche patient et le courrier confrère : mieux vaut que la place soit
 * prise, et que ce qui manque soit écrit, plutôt qu'un lien mort.
 */
export default function CorrespondantsPage() {
  return (
    <div className="page">
      <EnTetePage surTitre="Chantier à venir" titre="Correspondants" />

      <Carte titre="Ce que cet écran fera">
        <EtatVide titre="Rien à afficher pour l’instant">
          Le carnet des correspondants n’est pas encore construit.
        </EtatVide>
        <ul className="liste-simple">
          <li>Le carnet des confrères et praticiens adressants : nom, spécialité, adresse.</li>
          <li>
            Le rattachement d’un patient à <strong>un ou plusieurs</strong> correspondants,
            depuis sa fiche.
          </li>
          <li>
            Le <strong>courrier confrère</strong> pré-adressé au bon correspondant, avec son
            en-tête, sans ressaisie.
          </li>
          <li>L’historique de ce qui lui a déjà été adressé, pour ce patient.</li>
        </ul>
        <p className="muted" style={{ margin: 0 }}>
          Oris produit déjà le courrier confrère ; c’est le carnet et le rattachement qui
          manquent. Tant qu’ils ne sont pas là, le destinataire se saisit à la main.
        </p>
      </Carte>
    </div>
  );
}
