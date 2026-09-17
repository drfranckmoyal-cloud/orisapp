import type { ClinicalFactView } from "@/lib/api";
import { ASSERTION, CERTAINTY, CLINICAL_STATUS, TEMPORALITY } from "@/lib/labels";

/** Axes sémantiques d'un fait, toujours écrits en toutes lettres. */
export function FactChips({ fact }: { fact: ClinicalFactView }) {
  const critical = fact.assertion !== "present" || fact.certainty !== "certain";
  return (
    <span style={{ display: "inline-flex", flexWrap: "wrap", gap: 4 }}>
      {fact.teeth.length > 0 && <span className="chip">dent {fact.teeth.join(", ")}</span>}
      <span className={`chip ${critical ? "chip-review" : ""}`}>{ASSERTION[fact.assertion]}</span>
      <span className="chip">{CLINICAL_STATUS[fact.clinical_status]}</span>
      <span className="chip">{CERTAINTY[fact.certainty]}</span>
      <span className="chip">{TEMPORALITY[fact.temporality]}</span>
    </span>
  );
}
