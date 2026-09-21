import { describe, expect, it } from "vitest";

import { estWeekend, jourDecale, libelleSemaine, lundiDe, nomDuJour } from "./dates";

describe("dates de la colonne semaine", () => {
  it("remonte au lundi, y compris depuis un dimanche", () => {
    expect(lundiDe("2026-09-22")).toBe("2026-09-21"); // mardi → lundi
    expect(lundiDe("2026-09-21")).toBe("2026-09-21"); // lundi → lui-même
    expect(lundiDe("2026-09-27")).toBe("2026-09-21"); // dimanche → lundi d'avant
  });

  it("franchit les fins de mois", () => {
    expect(jourDecale("2026-09-30", 1)).toBe("2026-10-01");
    expect(jourDecale("2026-10-01", -1)).toBe("2026-09-30");
  });

  it("n’écrit le mois qu’une fois quand la semaine n’en change pas", () => {
    expect(libelleSemaine("2026-09-21", 7)).toBe("21 – 27 sept.");
    expect(libelleSemaine("2026-09-28", 7)).toBe("28 sept. – 4 oct.");
  });

  it("nomme les jours proches par leur nom courant", () => {
    const aujourdhui = nomDuJour(new Date().toLocaleDateString("sv-SE"));
    expect(aujourdhui).toBe("Aujourd’hui");
  });

  it("reconnaît le week-end", () => {
    expect(estWeekend("2026-09-26")).toBe(true); // samedi
    expect(estWeekend("2026-09-25")).toBe(false); // vendredi
  });
});
