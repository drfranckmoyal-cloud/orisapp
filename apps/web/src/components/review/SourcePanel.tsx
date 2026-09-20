import type { Claim, ClinicalObject, TranscriptView } from "@/lib/api";
import { SPEAKER, formatClock } from "@/lib/labels";

import { FactChips } from "./FactChips";

export type Selection = { kind: "claim"; claim: Claim } | { kind: "fact"; factId: string } | null;

/** « Pourquoi Oris a écrit ça ? » (spec §30) : faits d'appui et paroles sources. */
export function SourcePanel({
  selection,
  clinicalObject,
  transcript,
  onClose,
  motDe,
}: {
  selection: Selection;
  clinicalObject: ClinicalObject;
  transcript: TranscriptView;
  onClose: () => void;
  motDe: (concept: string) => string;
}) {
  if (selection === null) {
    return (
      <p className="muted">
        Cliquez sur une phrase du document ou sur un fait pour afficher sa source.
      </p>
    );
  }
  const factIds = selection.kind === "claim" ? selection.claim.fact_ids : [selection.factId];
  const warningCodes = selection.kind === "claim" ? selection.claim.warning_codes : [];
  const facts = clinicalObject.facts.filter((fact) => factIds.includes(fact.fact_id));
  const segmentIds = new Set(facts.flatMap((fact) => fact.evidence_segment_ids));
  const segments = transcript.segments.filter((segment) => segmentIds.has(segment.segment_id));
  const warnings = clinicalObject.warnings.filter((warning) => warningCodes.includes(warning.code));

  return (
    <div style={{ display: "grid", gap: 12 }}>
      {selection.kind === "claim" && <p style={{ margin: 0, fontWeight: 600 }}>« {selection.claim.text} »</p>}
      {warnings.map((warning) => (
        <p key={warning.code} className="muted">
          Phrase issue de l’alerte {warning.code} : {warning.message}
        </p>
      ))}
      {facts.map((fact) => (
        <div key={fact.fact_id} style={{ display: "grid", gap: 4 }}>
          <span>
            <strong>{motDe(fact.concept)}</strong>
            {typeof fact.value === "string" && fact.value ? ` : ${fact.value}` : ""}
            {fact.manually_validated && " · vérifié par vous"}
          </span>
          <FactChips fact={fact} />
        </div>
      ))}
      {segments.length > 0 && (
        <div style={{ display: "grid", gap: 8 }}>
          {segments.map((segment) => (
            <blockquote key={segment.segment_id} style={{ margin: 0, paddingLeft: 12, borderLeft: "3px solid var(--color-misty-teal)" }}>
              <div className="muted">
                {SPEAKER[segment.speaker_role] ?? segment.speaker_role} — {formatClock(segment.start_ms)}
              </div>
              « {segment.text} »
            </blockquote>
          ))}
        </div>
      )}
      {facts.some((fact) => fact.source_type === "manual") && (
        <p className="muted">Fait saisi par le praticien : pas de parole source.</p>
      )}
      <div>
        <button type="button" className="link-button" onClick={onClose}>
          Fermer la source
        </button>
      </div>
    </div>
  );
}
