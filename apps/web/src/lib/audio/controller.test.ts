import { describe, expect, it, vi } from "vitest";

import { CHUNK_SAMPLES } from "./chunker";
import { type CaptureApi, CaptureController, type FinishOutcome } from "./controller";
import { type AudioSource, CaptureError } from "./sources";
import { type QueueItem, type SendResult, Uploader } from "./uploader";

class FakeSource implements AudioSource {
  onSamples: ((samples: Float32Array, rate: number) => void) | null = null;
  onEnded: (() => void) | null = null;
  stopped = false;

  constructor(private readonly failure: CaptureError | null = null) {}

  async start(onSamples: (s: Float32Array, r: number) => void, onEnded: () => void): Promise<void> {
    if (this.failure) throw this.failure;
    this.onSamples = onSamples;
    this.onEnded = onEnded;
  }

  stop(): void {
    this.stopped = true;
  }

  emit(seconds: number): void {
    this.onSamples?.(new Float32Array(16_000 * seconds).fill(0.1), 16_000);
  }
}

function setup(options: { sourceFailure?: CaptureError; online?: () => boolean } = {}) {
  const sent: QueueItem[] = [];
  const sources: FakeSource[] = [];
  let clock = 1_000_000;
  const transport = {
    async send(item: QueueItem): Promise<SendResult> {
      if (options.online && !options.online()) return { ok: false, retry: true, code: "NETWORK_UNREACHABLE" };
      sent.push(item);
      return { ok: true };
    },
  };
  const finishCalls: { finalSequence: number; recordedMs: number; acceptGaps: boolean }[] = [];
  const api: CaptureApi = {
    start: vi.fn(async () => undefined),
    finish: vi.fn(async (args): Promise<FinishOutcome> => {
      finishCalls.push(args);
      return { status: "finished", missing: [] };
    }),
  };
  const controller = new CaptureController({
    api,
    transport,
    uploader: new Uploader(transport, [1], (callback) => setTimeout(callback, 1)),
    createSource: () => {
      const source = new FakeSource(options.sourceFailure ?? null);
      sources.push(source);
      return source;
    },
    maxSessionMs: 60_000,
    warnSessionMs: 50_000,
    now: () => clock,
  });
  return {
    controller,
    api,
    sent,
    sources,
    finishCalls,
    advance: (ms: number) => {
      clock += ms;
    },
  };
}

const kinds = (items: QueueItem[]) =>
  items.map((item) => (item.kind === "chunk" ? `chunk${item.chunk.sequence}` : item.kind));

describe("CaptureController", () => {
  it("records, pauses, resumes and finishes with every chunk acknowledged", async () => {
    const { controller, api, sent, sources, finishCalls } = setup();
    await controller.start(true);
    expect(api.start).toHaveBeenCalledWith(true);
    expect(controller.state.phase).toBe("recording");

    sources[0]!.emit(3); // 1 segment complet + 1 s en cours
    expect(controller.state.recordedMs).toBe(3000);
    controller.pause();
    expect(controller.state.phase).toBe("paused");
    expect(sources[0]!.stopped).toBe(true); // micro libéré pendant la pause
    sources[0]!.emit(5); // ignoré : source arrêtée
    await controller.resume();
    sources[1]!.emit(2);
    await controller.finish();

    expect(kinds(sent)).toEqual(["chunk0", "chunk1", "pause", "resume", "chunk2"]);
    expect(finishCalls).toEqual([{ finalSequence: 2, recordedMs: 5000, acceptGaps: false }]);
    expect(controller.state.phase).toBe("finished");
    const timestamps = sent.flatMap((i) => (i.kind === "chunk" ? [[i.chunk.timestampMs, i.chunk.durationMs]] : []));
    expect(timestamps).toEqual([[0, 2000], [2000, 1000], [3000, 2000]]); // pause exclue, sans trou
  });

  it("explains a refused microphone permission and does not start the consultation", async () => {
    const { controller, api } = setup({ sourceFailure: new CaptureError("permission_denied") });
    await controller.start(true);
    expect(controller.state).toMatchObject({ phase: "error", errorCode: "permission_denied" });
    expect(api.start).not.toHaveBeenCalled();
  });

  it("turns a lost microphone into a reported gap with its duration", async () => {
    const { controller, sent, sources, advance } = setup();
    await controller.start(true);
    sources[0]!.emit(2);
    sources[0]!.onEnded?.();
    expect(controller.state.phase).toBe("microphone_lost");
    advance(12_000);
    await controller.resume();
    sources[1]!.emit(2);
    await controller.finish();
    const gap = sent.find((item) => item.kind === "gap");
    expect(gap).toEqual({ kind: "gap", reason: "microphone_lost", durationMs: 12_000 });
  });

  it("keeps capturing during a network outage and sends everything once back online", async () => {
    let online = false;
    const { controller, sent, sources } = setup({ online: () => online });
    await controller.start(true);
    sources[0]!.emit(6);
    await new Promise((resolve) => setTimeout(resolve, 10));
    expect(controller.state.network).toBe("reconnecting");
    expect(controller.state.pendingUploads).toBe(3);
    expect(controller.state.phase).toBe("recording");
    online = true;
    await controller.finish();
    expect(kinds(sent)).toEqual(["chunk0", "chunk1", "chunk2"]);
    expect(controller.state.network).toBe("online");
  });

  it("lets the practitioner finish anyway, declaring unsent audio as a gap", async () => {
    const { controller, sources, finishCalls } = setup({ online: () => false });
    await controller.start(true);
    sources[0]!.emit(4);
    const pending = controller.finish();
    await new Promise((resolve) => setTimeout(resolve, 5));
    expect(controller.state.phase).toBe("finishing");
    await controller.finish(true);
    await pending;
    expect(finishCalls).toEqual([{ finalSequence: 1, recordedMs: 4000, acceptGaps: true }]);
  });

  it("pauses automatically at the maximum duration and warns before", async () => {
    const { controller, sources } = setup();
    await controller.start(true);
    sources[0]!.emit(52);
    expect(controller.state.warnDurationReached).toBe(true);
    expect(controller.state.phase).toBe("recording");
    sources[0]!.emit(10);
    expect(controller.state).toMatchObject({ phase: "paused", maxDurationReached: true });
    await controller.resume();
    expect(controller.state.phase).toBe("paused");
  });

  it("reports the interruption when resuming after a page reload", async () => {
    const { controller, sent, sources } = setup();
    await controller.resumeAfterReload(30_000, false);
    sources[0]!.emit(2);
    await controller.finish();
    expect(kinds(sent)).toEqual(["gap", "chunk0"]);
    expect(CHUNK_SAMPLES).toBe(32_000);
  });
});
