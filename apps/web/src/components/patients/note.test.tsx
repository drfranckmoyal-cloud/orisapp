import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NoteDictee } from "./NoteDictee";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("note dictée", () => {
  it("n’enregistre que si la note a changé", () => {
    const enregistrer = vi.fn(async () => undefined);
    render(
      <NoteDictee
        patientId="p1"
        valeur="Préfère le matin."
        initiale="Préfère le matin."
        onChange={() => undefined}
        onEnregistrer={enregistrer}
      />,
    );
    fireEvent.blur(screen.getByLabelText("Note administrative"));
    expect(enregistrer).not.toHaveBeenCalled();
  });

  it("enregistre en quittant le champ et le dit", async () => {
    const enregistrer = vi.fn(async () => undefined);
    render(
      <NoteDictee
        patientId="p1"
        valeur="À rappeler la veille."
        initiale=""
        onChange={() => undefined}
        onEnregistrer={enregistrer}
      />,
    );
    fireEvent.blur(screen.getByLabelText("Note administrative"), {
      target: { value: "À rappeler la veille." },
    });
    await waitFor(() => expect(screen.getByText("enregistrée")).toBeTruthy());
    expect(enregistrer).toHaveBeenCalledWith("À rappeler la veille.");
  });

  it("dit ce qu’elle est : un rappel qu’Oris ne lit pas", () => {
    render(
      <NoteDictee
        patientId="p1"
        valeur=""
        initiale=""
        onChange={() => undefined}
        onEnregistrer={async () => undefined}
      />,
    );
    const champ = screen.getByLabelText("Note administrative");
    expect(champ.getAttribute("placeholder")).toContain("Oris ne la lit pas");
    expect(screen.getByRole("button", { name: /Dicter la note/ })).toBeTruthy();
  });
});
