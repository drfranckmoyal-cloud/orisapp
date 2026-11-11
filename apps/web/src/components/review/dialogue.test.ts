import { describe, expect, it } from "vitest";

import {
  type DemandeServeur,
  type EtatDialogue,
  filDe,
  marqueDe,
  occupe,
  part,
  type Echange,
} from "./dialogueCorrection";

/** Franck, le 11/11/2026 : « garder l'historique, ne pas en remettre une vierge, et marquer
 *  les demandes traitées » — y compris l'app fermée. La conversation vit sur le serveur. */
const VIDE: EtatDialogue = { enVol: [], surcharges: {}, coches: {}, compteur: 0 };

function demande(etat: DemandeServeur["etat"], extra: Partial<DemandeServeur> = {}): DemandeServeur {
  return {
    id: "d-1",
    document_id: null,
    texte: "plus court",
    etat,
    lecture: null,
    propositions: [],
    message: "",
    code: "",
    created_at: "2026-11-11T08:00:00Z",
    depuis: "2026-11-11T08:00:05Z",
    ...extra,
  };
}

describe("le dialogue de correction", () => {
  it("affiche la conversation du serveur, demande et réponse", () => {
    const fil = filDe([demande("traitee", { message: "Document rédigé." })], VIDE, (c) => c);
    expect(fil.map((e) => e.qui)).toEqual(["moi", "oris"]);
    expect(marqueDe(fil[1])?.texte).toBe("Traitée");
  });

  it("dit pourquoi une demande n'a pas abouti, d'après le code gardé", () => {
    const fil = filDe([demande("echec", { code: "ANTHROPIC_AUTH" })], VIDE, () => "clé refusée");
    expect(fil[1]).toMatchObject({ sorte: "erreur", texte: "clé refusée" });
    expect(marqueDe(fil[1])?.texte).toBe("Non aboutie");
  });

  it("ajoute ce qui part à l'instant, et ce qu'on vient de confirmer", () => {
    const enCours: Echange = { id: "d-1", qui: "oris", sorte: "application", depuis: Date.now() };
    const fil = filDe([demande("proposee")], { ...VIDE, surcharges: { "d-1": enCours } }, (c) => c);
    expect(marqueDe(fil[1])?.texte).toBe("En cours");
    expect(occupe(fil)).toBe(true);
  });

  it("ne prétend jamais avoir fini", () => {
    expect(part(30)).toBeCloseTo(0.5, 1);
    expect(part(10_000)).toBeLessThanOrEqual(0.95);
  });
});
