import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AlerteNavigateur, INTERVALLE_MS, RAPPELS_MAX } from "./alerte";

/** Un AudioContext de pacotille : on ne veut pas du son, on veut savoir qu'il a sonné. */
function contexteFactice() {
  const departs: number[] = [];
  class FauxOscillateur {
    frequency = { value: 0 };
    connect(suite: unknown) {
      return suite as { connect: (d: unknown) => unknown };
    }
    start(quand: number) {
      departs.push(quand);
    }
    stop() {}
  }
  class FauxContexte {
    currentTime = 0;
    destination = {};
    async resume() {}
    createOscillator() {
      return new FauxOscillateur();
    }
    createGain() {
      return {
        gain: { setValueAtTime() {}, exponentialRampToValueAtTime() {} },
        connect: (suite: unknown) => suite,
      };
    }
  }
  return { FauxContexte, departs };
}

describe("l'alerte d'une écoute coupée", () => {
  const { FauxContexte, departs } = contexteFactice();

  beforeEach(() => {
    vi.useFakeTimers();
    departs.length = 0;
    (window as unknown as { AudioContext: unknown }).AudioContext = FauxContexte;
    document.title = "Oris";
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("insiste jusqu'à ce que l'écoute reprenne, puis se tait", () => {
    const alerte = new AlerteNavigateur();
    alerte.couper("micro_perdu");
    // Le motif entier part dès la coupure : trois notes, deux fois, deux voix chacune.
    expect(departs.length).toBe(3 * 2 * 2);
    expect(document.title).toContain("Oris a perdu le micro");

    vi.advanceTimersByTime(INTERVALLE_MS * 3);
    expect(departs.length).toBe(3 * 2 * 2 * 4);

    alerte.taire();
    vi.advanceTimersByTime(INTERVALLE_MS * 5);
    expect(departs.length).toBe(3 * 2 * 2 * 4);
    expect(document.title).toBe("Oris");
  });

  it("ne sonne pas indéfiniment : au bout d'un moment, l'avis suffit", () => {
    const alerte = new AlerteNavigateur();
    alerte.couper("micro_perdu");
    vi.advanceTimersByTime(INTERVALLE_MS * (RAPPELS_MAX + 10));
    expect(departs.length).toBe(3 * 2 * 2 * RAPPELS_MAX);
    alerte.taire();
  });

  it("une deuxième coupure ne fait pas sonner deux alertes à la fois", () => {
    const alerte = new AlerteNavigateur();
    alerte.couper("micro_perdu");
    alerte.couper("micro_perdu");
    const apresLesDeux = departs.length;
    vi.advanceTimersByTime(INTERVALLE_MS);
    expect(departs.length).toBe(apresLesDeux + 3 * 2 * 2);
    alerte.taire();
  });
});
