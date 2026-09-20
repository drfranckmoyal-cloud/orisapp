import styles from "./JetonPraticien.module.css";

/** Deux lettres pour un praticien : « Dr Franck Moyal » donne FM. */
export function initiales(nom: string): string {
  const mots = nom
    .replace(/^(Dr|Docteur|Pr)\.?\s+/i, "")
    .split(/[\s-]+/)
    .filter(Boolean);
  return mots.slice(0, 2).map((mot) => mot[0]?.toUpperCase() ?? "").join("") || "—";
}

/** La vignette du praticien qui a mené la consultation.
 *
 * Dans un cabinet à plusieurs, savoir de qui vient un compte rendu change tout —
 * et deux lettres suffisent pour le savoir sans lire. Le nom complet apparaît au
 * survol, pour lever le doute entre deux confrères aux mêmes initiales.
 */
export function JetonPraticien({
  nom,
  titre = "",
  taille = "normal",
}: {
  nom: string;
  titre?: string;
  taille?: "normal" | "petit";
}) {
  if (!nom) return null;
  const complet = `${titre} ${nom}`.trim();
  return (
    <span
      className={`${styles.jeton} ${taille === "petit" ? styles.petit : ""}`}
      title={complet}
      aria-label={`Consultation menée par ${complet}`}
    >
      {initiales(nom)}
    </span>
  );
}
