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

/** Pendant l'écoute : les barres du symbole suivent la voix (niveau 0…1). Au repos elles
 *  sont basses ; elles montent quand on parle — on voit que le micro entend. */
const BARRES_SYMBOLE = [
  { x: 13, y: 38, h: 34, poids: 0.8 },
  { x: 31, y: 20, h: 76, poids: 1 },
  { x: 49, y: 30, h: 48, poids: 0.9 },
  { x: 67, y: 20, h: 76, poids: 0.95 },
  { x: 85, y: 38, h: 34, poids: 0.85 },
];

export function SymboleVoix({ niveau, taille = 62 }: { niveau: number; taille?: number }) {
  const n = Math.min(1, Math.max(0, niveau));
  return (
    <svg
      viewBox="0 0 120 120"
      width={taille}
      height={taille}
      fill="currentColor"
      aria-hidden="true"
      focusable="false"
    >
      {BARRES_SYMBOLE.map((b) => (
        <rect
          key={b.x}
          x={b.x}
          y={b.y}
          width={10}
          height={b.h}
          rx={5}
          style={{
            transformBox: "fill-box",
            transformOrigin: "center",
            transform: `scaleY(${0.22 + 0.78 * n * b.poids})`,
            transition: "transform 90ms linear",
          }}
        />
      ))}
    </svg>
  );
}
