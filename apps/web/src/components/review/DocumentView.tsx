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
}: {
  document: DocumentData;
  selected: Claim | null;
  onSelect: (claim: Claim) => void;
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
    return <p className="muted">Document vide : aucun fait clinique à rédiger.</p>;
  }
  return (
    <div className={styles.document}>
      {/* Le rail montre déjà la source au clic — encore faut-il savoir que c'est
          cliquable : le même mot que sur l'iPhone. */}
      <p className={styles.indicePreuve}>
        Cliquez une phrase pour voir d’où elle vient.
      </p>
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
                  onClick={() => onSelect(claim)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelect(claim);
                    }
                  }}
                >
                  {avecGras(claim.text)}{" "}
                </span>
              ))}
            </p>
          ))}
        </section>
      ))}
    </div>
  );
}
