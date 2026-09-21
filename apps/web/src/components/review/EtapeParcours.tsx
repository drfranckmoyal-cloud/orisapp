import type { ReactNode } from "react";

import styles from "./parcours.module.css";

/** Une des trois étapes d'un document : 1 rédiger et valider, 2 documenter, 3 envoyer.
 *
 * Un grand numéro dans sa couleur, relié au suivant par une barre verticale : on voit
 * d'un coup d'œil où l'on en est. Une étape faite prend une coche.
 */
export function EtapeParcours({
  numero,
  teinte,
  fait = false,
  dernier = false,
  children,
}: {
  numero: number;
  teinte: "redaction" | "documentation" | "envoi";
  fait?: boolean;
  dernier?: boolean;
  children: ReactNode;
}) {
  return (
    <section
      className={styles.etape}
      data-teinte={teinte}
      data-fait={fait}
      data-dernier={dernier}
    >
      <div className={styles.rail} aria-hidden="true">
        <span className={styles.numero}>{fait ? "✓" : numero}</span>
      </div>
      <div className={styles.corps}>{children}</div>
    </section>
  );
}
