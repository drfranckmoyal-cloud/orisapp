import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Patient } from "@/lib/api";

import { NoteAdministrative } from "./NoteAdministrative";

afterEach(cleanup);

const patient = {
  id: "p1",
  first_name: "Marie",
  last_name: "Dupont",
  birth_date: null,
  external_id: null,
  note: "Préfère le matin.",
  created_at: "2026-09-20T09:00:00Z",
} as unknown as Patient;

describe("note administrative", () => {
  it("dit clairement qu’Oris ne la lit pas", () => {
    render(<NoteAdministrative patient={patient} onSaved={() => undefined} />);
    expect(screen.getByText(/Oris ne la lit pas/)).toBeTruthy();
  });

  it("n’active « Enregistrer » que si la note a changé", () => {
    render(<NoteAdministrative patient={patient} onSaved={() => undefined} />);
    const bouton = screen.getByRole("button", { name: /Enregistrer la note/ });
    expect(bouton).toHaveProperty("disabled", true);
    fireEvent.change(screen.getByLabelText("Note administrative"), {
      target: { value: "À rappeler au cabinet." },
    });
    expect(bouton).toHaveProperty("disabled", false);
  });

  it("envoie la note et prévient l’écran", async () => {
    const reponse = () =>
      Promise.resolve(new Response(JSON.stringify({ ...patient, note: "x" }), { status: 200 }));
    const fetchMock = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(reponse);
    vi.stubGlobal("fetch", fetchMock);
    const onSaved = vi.fn();
    render(<NoteAdministrative patient={patient} onSaved={onSaved} />);
    fireEvent.change(screen.getByLabelText("Note administrative"), {
      target: { value: "À rappeler au cabinet." },
    });
    fireEvent.click(screen.getByRole("button", { name: /Enregistrer la note/ }));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    const [, options] = fetchMock.mock.calls[0] ?? [];
    const corps = JSON.parse(String(options?.body));
    expect(corps).toEqual({ note: "À rappeler au cabinet." });
    vi.unstubAllGlobals();
  });
});
