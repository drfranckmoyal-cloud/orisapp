import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ApiStatus } from "./ApiStatus";

afterEach(cleanup);

describe("ApiStatus", () => {
  it("states in words that the server is unreachable", async () => {
    render(<ApiStatus load={async () => ({ state: "unreachable" })} />);
    expect(await screen.findByText("Serveur Oris injoignable")).toBeTruthy();
  });

  it("states that no real AI is connected when all providers are mocks", async () => {
    const load = async () =>
      ({
        state: "reachable",
        health: {
          status: "ok",
          service: "oris-api",
          version: "0.1.0",
          environment: "local",
          providers: {
            speech_to_text: "mock",
            clinical_extraction: "mock",
            document_generation: "mock",
            clinical_validation: "mock",
          },
        },
      }) as const;
    render(<ApiStatus load={load} />);
    expect(await screen.findByText(/Serveur Oris connecté/)).toBeTruthy();
    expect(screen.getByText(/aucun moteur d’IA réel/)).toBeTruthy();
  });
});
