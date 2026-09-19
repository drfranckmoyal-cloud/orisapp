import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ClinicalObject, Encounter } from "@/lib/api";

import { TreatmentPlanCards } from "./TreatmentPlanCards";

afterEach(cleanup);

const fact: ClinicalObject["facts"][number] = {
  fact_id: "f1",
  category: "clinical_finding",
  concept: "shape_asymmetry",
  value: "asymétrie de forme",
  teeth: ["23", "11"],
  surfaces: [],
  assertion: "present",
  temporality: "current",
  clinical_status: "observed",
  speaker_role: "practitioner",
  certainty: "certain",
  source_type: "audio",
  evidence_segment_ids: ["s1"],
  confidence: 0.9,
  manually_validated: false,
};

const clinicalObject: ClinicalObject = {
  encounter_id: "e",
  patient_id: "p",
  practitioner_id: "u",
  started_at: "2026-09-19T09:00:00Z",
  ended_at: null,
  status: "review",
  object_version: 1,
  facts: [fact],
  treatment_plan: {
    plan_id: "plan1",
    status: "draft",
    goals: [],
    notes: [],
    items: [
      {
        item_id: "i2",
        teeth: ["23"],
        problem: null,
        action: "facettes",
        status: "discussed",
        priority: "routine",
        sequence: null,
        alternatives: [],
        prerequisites: [],
        uncertainties: [],
        evidence_fact_ids: [],
      },
      {
        item_id: "i1",
        teeth: ["23", "11"],
        problem: "asymétrie de forme",
        action: "composites additifs",
        status: "proposed",
        priority: "routine",
        sequence: 1,
        alternatives: ["blanchiment"],
        prerequisites: ["empreinte optique"],
        uncertainties: ["décision définitive non prise"],
        evidence_fact_ids: ["f1"],
      },
    ],
  },
  procedures: [],
  warnings: [],
};

const encounter = { id: "e", status: "review" } as Encounter;

describe("TreatmentPlanCards", () => {
  it("shows each plan item with its teeth, status and reason", () => {
    render(
      <TreatmentPlanCards
        encounter={encounter}
        clinicalObject={clinicalObject}
        onSelectFact={vi.fn()}
        onCorrected={vi.fn()}
      />,
    );
    const card = screen.getByRole("article", { name: "composites additifs" });
    expect(card.textContent).toContain("dent 23, 11");
    expect(card.textContent).toContain("proposé");
    expect(card.textContent).toContain("Motif : asymétrie de forme");
    expect(card.textContent).toContain("Alternatives évoquées : blanchiment.");
    expect(card.textContent).toContain("Préalables : empreinte optique.");
    expect(card.textContent).toContain("Incertitudes : décision définitive non prise.");
    // La séquence n'est numérotée que si elle a été énoncée.
    expect(card.textContent).toContain("étape 1");
    expect(screen.getByRole("article", { name: "facettes" }).textContent).not.toContain("étape");
  });

  it("orders sequenced items first", () => {
    render(
      <TreatmentPlanCards
        encounter={encounter}
        clinicalObject={clinicalObject}
        onSelectFact={vi.fn()}
        onCorrected={vi.fn()}
      />,
    );
    const titles = screen.getAllByRole("article").map((card) => card.getAttribute("aria-label"));
    expect(titles).toEqual(["composites additifs", "facettes"]);
  });

  it("opens the source of the fact that justifies an item", () => {
    const onSelectFact = vi.fn();
    render(
      <TreatmentPlanCards
        encounter={encounter}
        clinicalObject={clinicalObject}
        onSelectFact={onSelectFact}
        onCorrected={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "asymétrie de forme (23, 11)" }));
    expect(onSelectFact).toHaveBeenCalledWith("f1");
  });

  it("says so when nothing was planned out loud", () => {
    render(
      <TreatmentPlanCards
        encounter={encounter}
        clinicalObject={{ ...clinicalObject, treatment_plan: null }}
        onSelectFact={vi.fn()}
        onCorrected={vi.fn()}
      />,
    );
    expect(screen.getByText(/Aucun élément de plan/).textContent).toBeTruthy();
  });

  it("cannot change a status while the consultation is still being recorded", () => {
    render(
      <TreatmentPlanCards
        encounter={{ ...encounter, status: "recording" } as Encounter}
        clinicalObject={clinicalObject}
        onSelectFact={vi.fn()}
        onCorrected={vi.fn()}
      />,
    );
    for (const select of screen.getAllByRole("combobox")) {
      expect((select as HTMLSelectElement).disabled).toBe(true);
    }
  });
});
