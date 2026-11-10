import type { ReactNode } from "react";

import type { Claim, DocumentView as DocumentData } from "@/lib/api";

import styles from "./review.module.css";

type Numerotee = { claim: Claim; index: number };

/** « une **agénésie** de 12 » : le passage entre doubles astérisques s'affiche en gras. */
export function avecGras(texte: string): ReactNode[] {
  return texte
    .split("**")
    .map((morceau, i) => (i % 2 === 1 ? <strong key={i}>{morceau}</strong> : morceau));
}

/** Le texte tel que le praticien l'a écrit : ses lignes, ses paragraphes, rien de plus.
 *
 * Oris ne le découpe pas en phrases : il ne sait pas d'où elles viennent, et faire comme
 * s'il le savait serait mentir. Les titres de rubrique s'y lisent comme il les a laissés.
 */
function TexteBrut({
  contenu,
  onEdit,
}: {
  contenu: string;
  onEdit?: ((position: number) => void) | undefined;
}) {
  return (
    <div className={styles.document} data-modifiable={Boolean(onEdit)}>
      {contenu.split(/\n{2,}/).map((bloc, i) => (
        <p
          key={i}
          className={styles.texteBrut}
          onClick={onEdit ? () => onEdit(Math.max(0, contenu.indexOf(bloc))) : undefined}
        >
          {bloc.split("\n").map((ligne, j) => (
            <span key={j}>
              {j > 0 && <br />}
              {avecGras(ligne)}
            </span>
          ))}
        </p>
      ))}
    </div>
  );
}

/** Les paragraphes d'une rubrique : ceux que le texte rédigé a découpés, sinon un seul. */
function paragraphes(claims: Numerotee[]): Numerotee[][] {
  const groupes: Numerotee[][] = [];
  let courant: number | null = null;
  for (const item of claims) {
    const rang = item.claim.paragraphe ?? -1;
    if (groupes.length === 0 || (rang >= 0 && rang !== courant)) groupes.push([]);
    groupes.at(-1)!.push(item);
    courant = rang;
  }
  return groupes;
}

/** Document rendu phrase par phrase ; chaque phrase ouvre sa source. */
export function DocumentBody({
  document,
  selected,
  onSelect,
  onEdit,
}: {
  document: DocumentData;
  selected: Claim | null;
  onSelect: (claim: Claim) => void;
  /** Le texte s'édite à même la page : un clic dans une phrase y pose le curseur. La
   *  source de la phrase passe alors par la petite cible qui la suit. */
  onEdit?: ((position: number) => void) | undefined;
}) {
  const flagged = new Set(
    document.validation_issues.flatMap((issue) =>
      issue.claim_index === null ? [] : [issue.claim_index],
    ),
  );
  const sections: { title: string; claims: Numerotee[] }[] = [];
  document.claims.forEach((claim, index) => {
    const last = sections.at(-1);
    if (last && last.title === claim.section) {
      last.claims.push({ claim, index });
    } else {
      sections.push({ title: claim.section, claims: [{ claim, index }] });
    }
  });

  if (sections.length === 0) {
    // Un texte réécrit à la main n'a plus de phrases rattachées aux faits — mais c'est
    // du texte, et c'est celui du praticien : l'écran annonçait « document vide » alors
    // que ses deux mille caractères étaient bien là (Franck, 10/10/2026).
    if (document.content.trim())
      return <TexteBrut contenu={document.content} onEdit={onEdit} />;
    return <p className="muted">Document vide : aucun fait clinique à rédiger.</p>;
  }
  return (
    <div className={styles.document} data-modifiable={Boolean(onEdit)}>
      {/* Le rail montre déjà la source au clic — encore faut-il savoir que c'est
          cliquable : le même mot que sur l'iPhone. */}
      {!onEdit && (
        <p className={styles.indicePreuve}>
          Cliquez une phrase pour voir d’où elle vient.
        </p>
      )}
      {sections.map((section) => (
        <section key={section.title} className={styles.rubrique}>
          <h3 className={styles.sectionTitle}>{section.title}</h3>
          {/* Des paragraphes courts, aérés ; chaque phrase reste cliquable pour ouvrir
              sa source. */}
          {paragraphes(section.claims).map((groupe) => (
            <p key={groupe[0]!.index} className={styles.paragraphe}>
              {groupe.map(({ claim, index }) => (
                // Un <span> et non un <button> : un bouton ne se coupe pas en fin de
                // ligne, la phrase ne coulerait pas dans le paragraphe.
                <span
                  key={index}
                  role="button"
                  tabIndex={0}
                  className={styles.claim}
                  data-selected={selected === claim}
                  data-flagged={flagged.has(index)}
                  onClick={() =>
                    onEdit
                      ? onEdit(Math.max(0, document.content.indexOf(claim.text)))
                      : onSelect(claim)
                  }
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelect(claim);
                    }
                  }}
                >
                  {avecGras(claim.text)}
                  {onEdit && (
                    <button
                      type="button"
                      className={styles.source}
                      title="D’où vient cette phrase ?"
                      aria-label="Voir d’où vient cette phrase"
                      onClick={(event) => {
                        event.stopPropagation();
                        onSelect(claim);
                      }}
                    >
                      <svg viewBox="0 0 20 20" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
                        <circle cx="10" cy="10" r="5.4" />
                        <path d="M10 2.4v3M10 14.6v3M2.4 10h3M14.6 10h3" />
                      </svg>
                    </button>
                  )}{" "}
                </span>
              ))}
            </p>
          ))}
        </section>
      ))}
    </div>
  );
}
