import { describe, expect, it } from "vitest";

describe("correctionDetail", () => {
  it("says which tooth replaced which", async () => {
    const { correctionDetail } = await import("./labels");
    expect(
      correctionDetail({
        before: { fact_id: "f1", concept: "crack", teeth: ["26"] },
        after: { fact_id: "f1", concept: "crack", teeth: ["27"] },
      }),
    ).toBe("26 → 27");
  });

  it("writes a plan status change in French", async () => {
    const { correctionDetail } = await import("./labels");
    expect(
      correctionDetail({
        before: { item_id: "i1", status: "proposed" },
        after: { item_id: "i1", status: "accepted" },
      }),
    ).toBe("proposé → accepté");
  });

  it("returns nothing when an event carries no comparable change", async () => {
    const { correctionDetail } = await import("./labels");
    expect(correctionDetail({ before: null, after: null })).toBeNull();
    expect(
      correctionDetail({ before: { fact_id: "f1" }, after: { fact_id: "f1" } }),
    ).toBeNull();
  });
});

describe("changeEnFrancais", () => {
  it("traduit les deux côtés d’un changement", async () => {
    const { changeEnFrancais } = await import("./labels");
    expect(changeEnFrancais("proposed → accepted")).toBe("proposé → accepté");
  });

  it("laisse les numéros de dents tels quels", async () => {
    const { changeEnFrancais } = await import("./labels");
    expect(changeEnFrancais("26 → 27")).toBe("26 → 27");
  });

  it("rend une chaîne sans flèche inchangée", async () => {
    const { changeEnFrancais } = await import("./labels");
    expect(changeEnFrancais("")).toBe("");
  });
});
