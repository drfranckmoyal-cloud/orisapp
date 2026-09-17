/**
 * Pilotage d'une écoute : source → rééchantillonnage → segments → file d'envoi.
 *
 * L'état est toujours explicite (spec §11, §65) : jamais d'écoute cachée, jamais de
 * trou masqué. Une perte de micro ou un rechargement de page devient un trou signalé.
 */

import { Chunker } from "./chunker";
import { Resampler, level as signalLevel, toInt16 } from "./pcm";
import { type AudioSource, CaptureError, type CaptureErrorCode } from "./sources";
import { type UploadTransport, Uploader, type UploaderStatus } from "./uploader";

export type CapturePhase =
  | "ready"
  | "starting"
  | "recording"
  | "paused"
  | "microphone_lost"
  | "finishing"
  | "finished"
  | "error";

export interface CaptureSnapshot {
  phase: CapturePhase;
  errorCode: CaptureErrorCode | string | null;
  recordedMs: number;
  level: number;
  network: "online" | "reconnecting";
  pendingUploads: number;
  lostUploads: number;
  maxDurationReached: boolean;
  warnDurationReached: boolean;
}

export interface FinishOutcome {
  status: "finished" | "chunks_missing";
  missing: string[];
}

export interface CaptureApi {
  start(patientInformed: boolean): Promise<void>;
  finish(options: { finalSequence: number; recordedMs: number; acceptGaps: boolean }): Promise<FinishOutcome>;
}

export interface ControllerOptions {
  api: CaptureApi;
  transport: UploadTransport;
  createSource: () => AudioSource;
  maxSessionMs: number;
  warnSessionMs: number;
  now?: () => number;
  uploader?: Uploader;
  /** Reprise d'une écoute existante (page rechargée). */
  resumeFrom?: { nextSequence: number; nextTimestampMs: number };
}

export class CaptureController {
  private readonly uploader: Uploader;
  private readonly chunker: Chunker;
  private source: AudioSource | null = null;
  private resampler: Resampler | null = null;
  private microphoneLostAt: number | null = null;
  private acceptGaps = false;
  private finishing: Promise<FinishOutcome> | null = null;
  private listeners = new Set<(snapshot: CaptureSnapshot) => void>();
  private snapshot: CaptureSnapshot;
  private readonly now: () => number;

  constructor(private readonly options: ControllerOptions) {
    this.now = options.now ?? (() => Date.now());
    this.uploader = options.uploader ?? new Uploader(options.transport);
    this.chunker = new Chunker(
      undefined,
      options.resumeFrom?.nextSequence ?? 0,
      options.resumeFrom?.nextTimestampMs ?? 0,
    );
    this.snapshot = {
      phase: "ready",
      errorCode: null,
      recordedMs: this.chunker.recordedMs,
      level: 0,
      network: "online",
      pendingUploads: 0,
      lostUploads: 0,
      maxDurationReached: false,
      warnDurationReached: false,
    };
    this.uploader.subscribe((status) => this.onUploads(status));
  }

  get state(): CaptureSnapshot {
    return this.snapshot;
  }

  subscribe(listener: (snapshot: CaptureSnapshot) => void): () => void {
    this.listeners.add(listener);
    listener(this.snapshot);
    return () => this.listeners.delete(listener);
  }

  /** Démarre : micro d'abord (autorisation), puis consultation côté serveur. */
  async start(patientInformed: boolean): Promise<void> {
    if (this.snapshot.phase !== "ready" && this.snapshot.phase !== "error") return;
    this.update({ phase: "starting", errorCode: null });
    if (!(await this.openSource())) return;
    try {
      await this.options.api.start(patientInformed);
    } catch (error) {
      this.closeSource();
      this.update({ phase: "error", errorCode: error instanceof Error ? error.message : "START_FAILED" });
      return;
    }
    this.update({ phase: "recording" });
  }

  /** Reprise après rechargement de page : l'écoute continuait côté serveur. */
  async resumeAfterReload(interruptionMs: number | null, wasPaused: boolean): Promise<void> {
    if (!wasPaused) {
      this.uploader.enqueue({ kind: "gap", reason: "page_reloaded", durationMs: interruptionMs });
    }
    this.update({ phase: "starting" });
    if (!(await this.openSource())) return;
    if (wasPaused) this.uploader.enqueue({ kind: "resume" });
    this.update({ phase: "recording" });
  }

  pause(): void {
    if (this.snapshot.phase !== "recording") return;
    this.flushChunk();
    this.closeSource();
    this.uploader.enqueue({ kind: "pause" });
    this.update({ phase: "paused", level: 0 });
  }

  async resume(): Promise<void> {
    const phase = this.snapshot.phase;
    if (phase !== "paused" && phase !== "microphone_lost") return;
    if (this.snapshot.maxDurationReached) return;
    if (!(await this.openSource())) return;
    if (phase === "paused") {
      this.uploader.enqueue({ kind: "resume" });
    } else {
      this.reportMicrophoneGap();
    }
    this.update({ phase: "recording", errorCode: null });
  }

  /**
   * Termine : vide la file d'envoi puis clôt côté serveur.
   * `acceptGaps` (« Terminer malgré tout ») abandonne les envois en attente : les
   * segments non reçus deviennent un trou déclaré, donc une alerte critique.
   */
  finish(acceptGaps = false): Promise<FinishOutcome> {
    if (acceptGaps) {
      this.acceptGaps = true;
      this.uploader.abandon();
    }
    if (!this.finishing) {
      this.finishing = this.completeFinish().finally(() => {
        this.finishing = null;
      });
    }
    return this.finishing;
  }

  private async completeFinish(): Promise<FinishOutcome> {
    if (this.snapshot.phase !== "finishing") {
      this.flushChunk();
      this.closeSource();
      if (this.snapshot.phase === "microphone_lost") this.reportMicrophoneGap();
      this.update({ phase: "finishing", level: 0, errorCode: null });
    }
    await this.uploader.whenDrained();
    try {
      const outcome = await this.options.api.finish({
        finalSequence: this.chunker.lastSequence,
        recordedMs: this.chunker.recordedMs,
        acceptGaps: this.acceptGaps || this.uploader.status.lost.length > 0,
      });
      if (outcome.status === "finished") this.update({ phase: "finished" });
      return outcome;
    } catch (error) {
      this.update({ errorCode: error instanceof Error ? error.message : "FINISH_FAILED" });
      throw error;
    }
  }

  /** Samples bruts de la source. */
  receive(samples: Float32Array, sampleRate: number): void {
    if (this.snapshot.phase !== "recording") return;
    if (!this.resampler || this.resampler.inputRate !== sampleRate) {
      this.resampler = new Resampler(sampleRate);
    }
    const pcm = toInt16(this.resampler.process(samples));
    for (const chunk of this.chunker.push(pcm)) {
      this.uploader.enqueue({ kind: "chunk", chunk });
    }
    const recordedMs = this.chunker.recordedMs;
    const patch: Partial<CaptureSnapshot> = { recordedMs, level: signalLevel(samples) };
    if (recordedMs >= this.options.warnSessionMs) patch.warnDurationReached = true;
    this.update(patch);
    if (recordedMs >= this.options.maxSessionMs) {
      // Durée maximale : pause automatique, rien n'est perdu (spec §12).
      this.update({ maxDurationReached: true });
      this.pause();
    }
  }

  private async openSource(): Promise<boolean> {
    const source = this.options.createSource();
    try {
      await source.start(
        (samples, rate) => this.receive(samples, rate),
        () => this.onSourceEnded(),
      );
    } catch (error) {
      const code = error instanceof CaptureError ? error.code : "capture_failed";
      const phase = this.snapshot.phase === "starting" ? "error" : this.snapshot.phase;
      this.update({ phase, errorCode: code });
      return false;
    }
    this.source = source;
    this.resampler = null;
    return true;
  }

  private closeSource(): void {
    this.source?.stop();
    this.source = null;
  }

  private onSourceEnded(): void {
    if (this.snapshot.phase !== "recording") return;
    this.flushChunk();
    this.closeSource();
    this.microphoneLostAt = this.now();
    this.update({ phase: "microphone_lost", errorCode: "microphone_lost", level: 0 });
  }

  private reportMicrophoneGap(): void {
    if (this.microphoneLostAt === null) return;
    this.uploader.enqueue({
      kind: "gap",
      reason: "microphone_lost",
      durationMs: Math.max(0, this.now() - this.microphoneLostAt),
    });
    this.microphoneLostAt = null;
  }

  private flushChunk(): void {
    const chunk = this.chunker.flush();
    if (chunk) this.uploader.enqueue({ kind: "chunk", chunk });
  }

  private onUploads(status: UploaderStatus): void {
    this.update({
      network: status.retrying ? "reconnecting" : "online",
      pendingUploads: status.pending,
      lostUploads: status.lost.length,
    });
  }

  private update(patch: Partial<CaptureSnapshot>): void {
    this.snapshot = { ...this.snapshot, ...patch };
    this.listeners.forEach((listener) => listener(this.snapshot));
  }
}
