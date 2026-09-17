import { describe, expect, it } from "vitest";

import { fetchHealth, type HealthResponse } from "./api";

const healthy: HealthResponse = {
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
};

function respond(body: unknown, status = 200): typeof fetch {
  return async () => new Response(JSON.stringify(body), { status });
}

describe("fetchHealth", () => {
  it("returns the health payload when the API answers", async () => {
    const result = await fetchHealth(respond(healthy), "http://api.test");
    expect(result).toEqual({ state: "reachable", health: healthy });
  });

  it("reports unreachable on HTTP error", async () => {
    expect(await fetchHealth(respond({}, 503), "http://api.test")).toEqual({ state: "unreachable" });
  });

  it("reports unreachable on network failure", async () => {
    const failing: typeof fetch = async () => {
      throw new TypeError("network");
    };
    expect(await fetchHealth(failing, "http://api.test")).toEqual({ state: "unreachable" });
  });

  it("rejects a payload that is not an Oris health response", async () => {
    expect(await fetchHealth(respond({ status: "ok" }), "http://api.test")).toEqual({
      state: "unreachable",
    });
  });
});

describe("apiRequest", () => {
  it("returns the parsed body", async () => {
    const { apiRequest } = await import("./api");
    expect(await apiRequest<{ ok: boolean }>("/x", {}, respond({ ok: true }), "http://api.test")).toEqual({
      ok: true,
    });
  });

  it("turns an API error into a coded ApiError", async () => {
    const { ApiError, apiRequest } = await import("./api");
    const failing = respond({ code: "WARNING_NOT_ACKNOWLEDGED", details: ["AUDIO_GAP"] }, 409);
    await expect(apiRequest("/x", { method: "POST", body: {} }, failing, "http://api.test")).rejects.toEqual(
      new ApiError(409, "WARNING_NOT_ACKNOWLEDGED", ["AUDIO_GAP"]),
    );
  });

  it("reports network failures", async () => {
    const { apiRequest } = await import("./api");
    const down: typeof fetch = async () => {
      throw new TypeError("down");
    };
    await expect(apiRequest("/x", {}, down, "http://api.test")).rejects.toMatchObject({
      code: "NETWORK_UNREACHABLE",
    });
  });
});
