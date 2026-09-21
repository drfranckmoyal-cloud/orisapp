import { RUBRIQUES, type TypeVisite } from "@/lib/modeles";

import styles from "./listening.module.css";

/** Le déroulé attendu, à côté de l'écoute : un aide-mémoire, pas une liste à cocher.
 *
 * Il ne bouge pas pendant la consultation — rien ici ne prétend savoir ce qui a été
 * dit. Il rappelle seulement les rubriques du modèle, pour ne pas oublier, par exemple,
 * les informations données au patient.
 */
export function Deroule({ type }: { type: TypeVisite }) {
  return (
    <aside className={styles.deroule} aria-label="Déroulé du compte rendu">
      <p className={styles.derouleTitre}>
        {type === "procedure"
          ? "Compte rendu opératoire"
          : "Compte rendu de consultation"}
      </p>
      <ol className={styles.derouleListe}>
        {RUBRIQUES[type].map((rubrique) => (
          <li key={rubrique.titre}>
            {rubrique.titre}
            {rubrique.detail && <small>{rubrique.detail}</small>}
          </li>
        ))}
      </ol>
    </aside>
  );
}
