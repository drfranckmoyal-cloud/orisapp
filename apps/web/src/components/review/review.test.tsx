import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ClinicalObject, DocumentView, TranscriptView } from "@/lib/api";
import { errorMessage } from "@/lib/labels";

import { DocumentBody } from "./DocumentView";
import { SourcePanel } from "./SourcePanel";

afterEach(cleanup);

const fact: ClinicalObject["facts"][number] = {
  fact_id: "f1",
  category: "assessment",
  concept: "crack",
  value: "possible",
  teeth: ["16"],
  surfaces: [],
  assertion: "uncertain",
  temporality: "current",
  clinical_status: "differential",
  speaker_role: "practitioner",
  certainty: "possible",
  source_type: "system_test",
  evidence_segment_ids: ["s1"],
  confidence: 0.96,
  manually_validated: false,
};

const clinicalObject: ClinicalObject = {
  encounter_id: "e",
  patient_id: "p",
  practitioner_id: "u",
  started_at: "2026-09-17T09:00:00Z",
  ended_at: null,
  status: "review",
  object_version: 1,
  facts: [fact],
  treatment_plan: null,
  procedures: [],
  warnings: [],
};

const transcript: TranscriptView = {
  encounter_id: "e",
  segments: [
    {
      segment_id: "s1",
      start_ms: 65000,
      end_ms: 68000,
      speaker_role: "practitioner",
      text: "Il y a peut-être une fissure sur 16.",
      confidence: 0.92,
      is_final: true,
    },
  ],
};

const document: DocumentView = {
  id: "d",
  encounter_id: "e",
  document_type: "consultation_note",
  status: "draft_ai",
  version: 1,
  generated_from_object_version: 1,
  is_current: true,
  content: "",
  claims: [
    {
      section: "Analyse / diagnostic / hypothèses",
      text: "Suspicion de fissure (16), non confirmée.",
      fact_ids: ["f1"],
      warning_codes: [],
    },
  ],
  supported_fact_ids: ["f1"],
  validation_issues: [],
  generator: "mock:0.2",
  created_at: "2026-09-17T09:00:00Z",
  validated_at: null,
};

describe("review screen", () => {
  it("opens the source of a sentence: facts with their axes and the spoken words", () => {
    const onSelect = vi.fn();
    render(<DocumentBody document={document} selected={null} onSelect={onSelect} />);
    fireEvent.click(screen.getByText("Suspicion de fissure (16), non confirmée."));
    expect(onSelect).toHaveBeenCalledWith(document.claims[0]);

    render(
      <SourcePanel
        selection={{ kind: "claim", claim: document.claims[0]! }}
        clinicalObject={clinicalObject}
        transcript={transcript}
        onClose={() => undefined}
        motDe={(concept) => concept}
      />,
    );
    expect(screen.getByText("« Il y a peut-être une fissure sur 16. »")).toBeTruthy();
    expect(screen.getByText("incertain")).toBeTruthy();
    expect(screen.getByText("hypothèse")).toBeTruthy();
    expect(screen.getByText(/Praticien — 01:05/)).toBeTruthy();
  });

  it("explains blocking API errors in French", () => {
    expect(errorMessage("WARNING_NOT_ACKNOWLEDGED")).toMatch(/alerte critique/);
    expect(errorMessage("SOMETHING_NEW")).toBe("Action impossible (SOMETHING_NEW).");
  });
});
