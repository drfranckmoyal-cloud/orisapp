import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TranscriptionDirecte } from "./TranscriptionDirecte";

afterEach(cleanup);

function repond(body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(body), { status: 200 })),
  );
}

beforeEach(() => vi.unstubAllGlobals());

describe("panneau « ce qu’Oris entend »", () => {
  it("ne s’affiche pas quand l’écoute en direct est éteinte", async () => {
    repond({ state: "disabled", segments: [], total: 0, reconnections: 0, error_code: null });
    const { container } = render(<TranscriptionDirecte encounterId="e1" />);
    await waitFor(() => expect(container.textContent).toBe(""));
  });

  it("reste replié et annonce ce qui est entendu", async () => {
    repond({
      state: "running",
      error_code: null,
      reconnections: 0,
      total: 3,
      segments: [
        {
          segment_id: "s1",
          start_ms: 0,
          end_ms: 1000,
          speaker_role: "practitioner",
          text: "Sur la vingt-six.",
          is_final: true,
        },
      ],
    });
    render(<TranscriptionDirecte encounterId="e1" />);
    await screen.findByText(/3 paroles entendues/);
    // Replié : le texte lui-même n’est pas encore là.
    expect(screen.queryByText("Sur la vingt-six.")).toBeNull();
  });

  it("dit que l’enregistrement continue si le direct tombe", async () => {
    repond({
      state: "failed",
      error_code: "RuntimeError",
      reconnections: 0,
      total: 0,
      segments: [],
    });
    render(<TranscriptionDirecte encounterId="e1" />);
    const bouton = await screen.findByRole("button", { name: /interrompue/ });
    fireEvent.click(bouton);
    await waitFor(() => expect(screen.getByText(/L’enregistrement continue/)).toBeTruthy());
  });
});
