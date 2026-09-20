/** Le symbole d'Oris : une ligne de son dont le profil dessine une molaire.
 *
 * Deux cuspides séparées d'un sillon en haut, deux racines en bas. Vu de loin,
 * un niveau sonore ; vu de près, une dent. Jamais de dent dessinée littéralement.
 *
 * `anime` fait bouger les barres comme un vumètre : réservé à l'écoute et au
 * survol du bouton qui la démarre. La marque n'illustre pas le produit, elle en
 * est l'instrument.
 */
export function Symbole({
  taille = 24,
  className,
  anime = false,
}: {
  taille?: number;
  className?: string;
  anime?: boolean;
}) {
  return (
    <svg
      viewBox="0 0 120 120"
      width={taille}
      height={taille}
      fill="currentColor"
      className={className}
      data-anime={anime ? "" : undefined}
      aria-hidden="true"
      focusable="false"
    >
      <rect x="13" y="38" width="10" height="34" rx="5" />
      <rect x="31" y="20" width="10" height="76" rx="5" />
      <rect x="49" y="30" width="10" height="48" rx="5" />
      <rect x="67" y="20" width="10" height="76" rx="5" />
      <rect x="85" y="38" width="10" height="34" rx="5" />
    </svg>
  );
}
