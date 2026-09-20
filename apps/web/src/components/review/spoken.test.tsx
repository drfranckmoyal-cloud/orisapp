import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ClinicalObject, Encounter } from "@/lib/api";

import { SpokenCorrectionPanel } from "./SpokenCorrection";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const clinicalObject = {
  object_version: 3,
  facts: [],
  treatment_plan: null,
  procedures: [],
  warnings: [],
} as unknown as ClinicalObject;

const encounter = { id: "e1", status: "review" } as Encounter;

function answer(body: unknown): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(body), { status: 200 })),
  );
}

function panel(onCorrected = vi.fn()) {
  return render(
    <SpokenCorrectionPanel
      encounter={encounter}
      clinicalObject={clinicalObject}
      onCorrected={onCorrected}
    />,
  );
}

describe("SpokenCorrectionPanel", () => {
  it("shows what Oris understood before anything is applied", async () => {
    answer({
      kind: "clinical",
      summary: "Remplacer la dent 26 par 27 (2 élément(s))",
      impact: "high",
      reason: "",
      candidates: [],
      operations: [{ operation: "replace_tooth" }],
      applied: false,
      object_version: 3,
    });
    panel();
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "remplace 26 par 27" } });
    fireEvent.click(screen.getByRole("button", { name: "Voir ce qu’Oris comprend" }));

    await waitFor(() =>
      expect(screen.getByText("Remplacer la dent 26 par 27 (2 élément(s))")).toBeTruthy(),
    );
    expect(screen.getByText(/touche le dossier clinique/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Appliquer la correction" })).toBeTruthy();
  });

  it("sends the expected object version only when applying", async () => {
    const calls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_url: string, init: RequestInit) => {
        calls.push(String(init.body));
        return new Response(
          JSON.stringify({
            kind: "clinical",
            summary: "Remplacer la dent 26 par 27",
            impact: "high",
            reason: "",
            candidates: [],
            operations: [],
            applied: calls.length > 1,
            object_version: 3,
          }),
          { status: 200 },
        );
      }),
    );
    const onCorrected = vi.fn();
    panel(onCorrected);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "remplace 26 par 27" } });
    fireEvent.click(screen.getByRole("button", { name: "Voir ce qu’Oris comprend" }));
    await waitFor(() => expect(calls.length).toBe(1));
    expect(calls[0]).not.toContain("expected_object_version");

    fireEvent.click(screen.getByRole("button", { name: "Appliquer la correction" }));
    await waitFor(() => expect(calls.length).toBe(2));
    expect(calls[1]).toContain('"expected_object_version":3');
    await waitFor(() => expect(onCorrected).toHaveBeenCalled());
  });

  it("explains an unclear command instead of offering to apply it", async () => {
    answer({
      kind: "unclear",
      summary: "Commande non comprise",
      impact: "normal",
      reason: "Précisez quel traitement change de statut.",
      candidates: ["composites additifs", "facettes"],
      operations: [],
      applied: false,
      object_version: 3,
    });
    panel();
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "il accepte" } });
    fireEvent.click(screen.getByRole("button", { name: "Voir ce qu’Oris comprend" }));

    await waitFor(() =>
      expect(screen.getByText("Précisez quel traitement change de statut.")).toBeTruthy(),
    );
    expect(screen.getByText("composites additifs")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Appliquer la correction" })).toBeNull();
  });

  it("offers to remember a style preference without touching the record", async () => {
    answer({
      kind: "editorial",
      summary: "Préférence de rédaction : compte rendu plus court",
      impact: "normal",
      reason: "Le dossier clinique n’est pas modifié : c’est une question de forme.",
      candidates: [],
      operations: [],
      applied: false,
      object_version: 3,
    });
    panel();
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "plus court" } });
    fireEvent.click(screen.getByRole("button", { name: "Voir ce qu’Oris comprend" }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Retenir la préférence" })).toBeTruthy(),
    );
  });
});
