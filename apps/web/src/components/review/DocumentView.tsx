import type { Claim, DocumentView as DocumentData } from "@/lib/api";

import styles from "./review.module.css";

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
    document.validation_issues.flatMap((issue) => (issue.claim_index === null ? [] : [issue.claim_index])),
  );
  const sections: { title: string; claims: { claim: Claim; index: number }[] }[] = [];
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
      {sections.map((section) => (
        <section key={section.title}>
          <h3 className={styles.sectionTitle}>{section.title}</h3>
          {/* Une rubrique se lit comme un paragraphe ; chaque phrase reste cliquable
              pour ouvrir sa source. */}
          <p className={styles.paragraphe}>
            {section.claims.map(({ claim, index }) => (
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
                {claim.text}
              </span>
            ))}
          </p>
        </section>
      ))}
    </div>
  );
}
