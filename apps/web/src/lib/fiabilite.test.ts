import { describe, expect, it } from "vitest";

import type { ClinicalFactView } from "@/lib/api";
import { fiabiliteDe } from "@/lib/fiabilite";

function fait(patch: Partial<ClinicalFactView> = {}): ClinicalFactView {
  return {
    fact_id: "f1",
    concept: "caries",
    value: null,
    teeth: ["26"],
    assertion: "present",
    certainty: "certain",
    temporality: "current",
    clinical_status: "observed",
    speaker_role: "clinician",
    confidence: 0.92,
    manually_validated: false,
    source_type: "extraction",
    evidence: [],
    ...patch,
  } as unknown as ClinicalFactView;
}

describe("fiabiliteDe", () => {
  it("dit fiable quand tout est net", () => {
    expect(fiabiliteDe(fait(), true).niveau).toBe("fiable");
  });

  it("signale un terme que Oris ne connaît pas", () => {
    expect(fiabiliteDe(fait(), false).niveau).toBe("a_verifier");
  });

  it("signale une voix non identifiée", () => {
    expect(fiabiliteDe(fait({ speaker_role: "unknown" }), true).niveau).toBe("a_verifier");
  });

  it("signale l’incertitude clinique", () => {
    expect(fiabiliteDe(fait({ certainty: "probable" }), true).niveau).toBe("a_verifier");
    expect(fiabiliteDe(fait({ assertion: "uncertain" }), true).niveau).toBe("a_verifier");
  });

  it("signale une reconnaissance peu sûre", () => {
    expect(fiabiliteDe(fait({ confidence: 0.4 }), true).niveau).toBe("a_verifier");
  });
});
