import { afterEach, describe, expect, it } from "vitest";

import {
  lireDialogue,
  marqueDe,
  modifierDialogue,
  occupe,
  part,
  type Echange,
} from "./dialogueCorrection";

/** Franck, le 11/11/2026 : « si je sors et que je reviens, garder l'historique, ne pas en
 *  remettre une vierge, et marquer les demandes traitées ». */
describe("le dialogue de correction", () => {
  afterEach(() => window.sessionStorage.clear());

  it("garde le fil d'une consultation quand on revient", () => {
    modifierDialogue("c1", (etat) => ({
      ...etat,
      compteur: 1,
      fil: [{ id: 1, qui: "moi", texte: "plus court" }],
    }));
    expect(lireDialogue("c1").fil).toHaveLength(1);
    expect(lireDialogue("c2").fil).toHaveLength(0);
    expect(window.sessionStorage.getItem("oris.dialogue.c1")).toContain("plus court");
  });

  it("marque chaque demande d'après ce qu'elle est devenue", () => {
    const fait: Echange = { id: 2, qui: "oris", sorte: "fait", texte: "Document rédigé." };
    const enCours: Echange = { id: 2, qui: "oris", sorte: "application", depuis: Date.now() };
    const annule: Echange = { id: 2, qui: "oris", sorte: "annule", texte: "Annulé." };
    expect(marqueDe(fait)?.texte).toBe("Traitée");
    expect(marqueDe(enCours)?.texte).toBe("En cours");
    expect(marqueDe(annule)?.texte).toBe("Annulée");
    expect(occupe([enCours])).toBe(true);
    expect(occupe([fait])).toBe(false);
  });

  it("ne prétend jamais avoir fini", () => {
    expect(part(30)).toBeCloseTo(0.5, 1);
    expect(part(10_000)).toBeLessThanOrEqual(0.95);
  });
});
