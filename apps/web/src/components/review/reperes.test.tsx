import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { ClinicalObject, TranscriptView } from "@/lib/api";

import { RailRevision } from "./RailRevision";

afterEach(cleanup);

const clinicalObject: ClinicalObject = {
  encounter_id: "e",
  patient_id: "p",
  practitioner_id: "u",
  started_at: "2026-09-20T09:00:00Z",
  ended_at: null,
  status: "review",
  object_version: 1,
  facts: [],
  treatment_plan: null,
  procedures: [],
  warnings: [],
};

const transcript: TranscriptView = {
  encounter_id: "e",
  segments: [
    {
      segment_id: "s1",
      start_ms: 5_000,
      end_ms: 9_000,
      speaker_role: "practitioner",
      text: "Trop tôt pour le repère.",
      confidence: 0.9,
      is_final: true,
    },
    {
      segment_id: "s2",
      start_ms: 115_000,
      end_ms: 119_000,
      speaker_role: "patient",
      text: "Ça me réveille la nuit.",
      confidence: 0.9,
      is_final: true,
    },
  ],
};

function rail(marks: { timestamp_ms: number; created_at: string }[]) {
  return render(
    <RailRevision
      document={undefined}
      clinicalObject={clinicalObject}
      versions={[]}
      transcript={transcript}
      learning={[]}
      marks={marks}
      selection={null}
      onSelect={() => undefined}
      motDe={(concept) => concept}
    />,
  );
}

describe("points marqués", () => {
  it("n’affiche pas l’onglet quand rien n’a été marqué", () => {
    rail([]);
    expect(screen.queryByRole("tab", { name: /Points marqués/ })).toBeNull();
  });

  it("montre ce qui se disait autour du moment marqué", () => {
    rail([{ timestamp_ms: 120_000, created_at: "2026-09-20T09:02:00Z" }]);
    fireEvent.click(screen.getByRole("tab", { name: /Points marqués \(1\)/ }));
    expect(screen.getByText("Ça me réveille la nuit.")).toBeTruthy();
    expect(screen.queryByText("Trop tôt pour le repère.")).toBeNull();
  });
});
