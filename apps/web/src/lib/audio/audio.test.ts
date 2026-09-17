import { describe, expect, it } from "vitest";

import { sha256Hex } from "./checksum";
import { CHUNK_SAMPLES, Chunker } from "./chunker";
import { Resampler, int16ToBytes, level, toInt16 } from "./pcm";
import { interpret } from "./transport";
import { type QueueItem, type SendResult, Uploader } from "./uploader";

function tick(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

describe("pcm", () => {
  it("downsamples 48 kHz to 16 kHz across blocks without losing samples", () => {
    const resampler = new Resampler(48_000);
    let total = 0;
    for (let block = 0; block < 10; block++) {
      total += resampler.process(new Float32Array(128).fill(0.5)).length;
    }
    expect(total).toBe(Math.floor((128 * 10) / 3));
  });

  it("keeps 16 kHz input untouched", () => {
    const input = Float32Array.from([0.1, -0.2]);
    expect(new Resampler(16_000).process(input)).toEqual(input);
  });

  it("converts to clamped 16-bit little-endian", () => {
    expect(Array.from(toInt16(Float32Array.from([1, -1, 2, 0])))).toEqual([32767, -32768, 32767, 0]);
    expect(Array.from(int16ToBytes(Int16Array.from([1, -2])))).toEqual([1, 0, 254, 255]);
  });

  it("measures silence as zero level", () => {
    expect(level(new Float32Array(100))).toBe(0);
    expect(level(new Float32Array(100).fill(0.5))).toBeGreaterThan(0.5);
  });
});

describe("chunker", () => {
  it("emits contiguous 2 s chunks with exact timestamps", () => {
    const chunker = new Chunker();
    const chunks = chunker.push(new Int16Array(CHUNK_SAMPLES * 2 + 8_000));
    expect(chunks.map((c) => [c.sequence, c.timestampMs, c.durationMs])).toEqual([
      [0, 0, 2000],
      [1, 2000, 2000],
    ]);
    expect(chunker.recordedMs).toBe(4500);
    const partial = chunker.flush();
    expect([partial?.sequence, partial?.timestampMs, partial?.durationMs]).toEqual([2, 4000, 500]);
    expect(chunker.flush()).toBeNull();
    expect(chunker.lastSequence).toBe(2);
  });

  it("continues numbering after a reload", () => {
    const chunker = new Chunker(CHUNK_SAMPLES, 7, 14_000);
    const [chunk] = chunker.push(new Int16Array(CHUNK_SAMPLES));
    expect([chunk?.sequence, chunk?.timestampMs]).toEqual([7, 14_000]);
  });
});

describe("checksum", () => {
  it("computes SHA-256 like the server", async () => {
    expect(await sha256Hex(new TextEncoder().encode("abc"))).toBe(
      "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
    );
  });
});

function chunkItem(sequence: number): QueueItem {
  return { kind: "chunk", chunk: { sequence, timestampMs: sequence * 2000, durationMs: 2000, samples: new Int16Array(4) } };
}

describe("uploader", () => {
  it("sends in order, one at a time, and removes items only after acknowledgement", async () => {
    const sent: number[] = [];
    let inFlight = 0;
    const uploader = new Uploader({
      async send(item) {
        inFlight += 1;
        expect(inFlight).toBe(1);
        await tick();
        if (item.kind === "chunk") sent.push(item.chunk.sequence);
        inFlight -= 1;
        return { ok: true };
      },
    });
    [0, 1, 2].forEach((s) => uploader.enqueue(chunkItem(s)));
    expect(uploader.status.pending).toBe(3);
    await uploader.whenDrained();
    expect(sent).toEqual([0, 1, 2]);
    expect(uploader.status.pending).toBe(0);
  });

  it("retries through a network outage without dropping or reordering", async () => {
    const delays: number[] = [];
    let online = false;
    const sent: string[] = [];
    const uploader = new Uploader(
      {
        async send(item) {
          if (!online) throw new TypeError("offline");
          sent.push(item.kind === "chunk" ? `chunk${item.chunk.sequence}` : item.kind);
          return { ok: true };
        },
      },
      [10, 20, 40],
      (callback, delay) => {
        delays.push(delay);
        if (delays.length === 4) online = true;
        setTimeout(callback, 0);
      },
    );
    const statuses: boolean[] = [];
    uploader.subscribe((status) => statuses.push(status.retrying));
    uploader.enqueue(chunkItem(0));
    uploader.enqueue({ kind: "pause" });
    uploader.enqueue(chunkItem(1));
    await uploader.whenDrained();
    expect(delays).toEqual([10, 20, 40, 40]);
    expect(sent).toEqual(["chunk0", "pause", "chunk1"]);
    expect(statuses).toContain(true);
    expect(uploader.status.retrying).toBe(false);
  });

  it("reports permanently rejected items as lost", async () => {
    const uploader = new Uploader({
      async send(item): Promise<SendResult> {
        return item.kind === "chunk" && item.chunk.sequence === 1
          ? { ok: false, retry: false, code: "CHUNK_CONFLICT" }
          : { ok: true };
      },
    });
    [0, 1, 2].forEach((s) => uploader.enqueue(chunkItem(s)));
    await uploader.whenDrained();
    expect(uploader.status.lost.map((l) => l.code)).toEqual(["CHUNK_CONFLICT"]);
  });

  it("can be abandoned explicitly while offline", async () => {
    const uploader = new Uploader(
      { send: async () => ({ ok: false, retry: true, code: "NETWORK_UNREACHABLE" }) },
      [10],
      (callback) => setTimeout(callback, 5),
    );
    uploader.enqueue(chunkItem(0));
    const drained = uploader.whenDrained();
    await tick();
    expect(uploader.abandon()).toHaveLength(1);
    await drained;
    expect(uploader.status.pending).toBe(0);
  });
});

describe("transport", () => {
  const response = (status: number, body: unknown) => new Response(JSON.stringify(body), { status });

  it("treats duplicates and already-applied pauses as success", async () => {
    expect(await interpret(response(200, { status: "duplicate" }))).toEqual({ ok: true });
    expect(await interpret(response(409, { code: "INVALID_TRANSITION" }))).toEqual({ ok: true });
  });

  it("retries transient errors but not conflicts", async () => {
    expect(await interpret(response(503, {}))).toMatchObject({ ok: false, retry: true });
    expect(await interpret(response(422, { code: "CHECKSUM_MISMATCH" }))).toMatchObject({ retry: true });
    expect(await interpret(response(409, { code: "CHUNK_CONFLICT" }))).toMatchObject({ retry: false });
  });
});
