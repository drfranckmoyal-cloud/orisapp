/**
 * File d'envoi ordonnée : segments audio et événements (pause, reprise, trou).
 *
 * - un seul envoi à la fois, dans l'ordre de capture ;
 * - un élément ne quitte la file qu'après accusé de réception du serveur ;
 * - erreur temporaire (réseau, 5xx) : nouvelle tentative avec attente croissante,
 *   sans limite tant que la session vit (spec §69 : rien n'est abandonné en silence) ;
 * - erreur définitive : l'élément est déclaré perdu et signalé.
 */

import type { PcmChunk } from "./chunker";

export type GapReason = "microphone_lost" | "page_reloaded" | "capture_error";

export type QueueItem =
  | { kind: "chunk"; chunk: PcmChunk }
  | { kind: "pause" }
  | { kind: "resume" }
  | { kind: "gap"; reason: GapReason; durationMs: number | null };

export type SendResult = { ok: true } | { ok: false; retry: boolean; code: string };

export interface UploadTransport {
  send(item: QueueItem): Promise<SendResult>;
}

export interface UploaderStatus {
  pending: number;
  pendingBytes: number;
  retrying: boolean;
  lastErrorCode: string | null;
  lost: { item: QueueItem; code: string }[];
}

type Schedule = (callback: () => void, delayMs: number) => void;

export const DEFAULT_BACKOFF_MS = [500, 1000, 2000, 4000, 8000];

export class Uploader {
  private queue: QueueItem[] = [];
  private running = false;
  private stopped = false;
  private retrying = false;
  private lastErrorCode: string | null = null;
  private lost: { item: QueueItem; code: string }[] = [];
  private listeners = new Set<(status: UploaderStatus) => void>();
  private drainWaiters: (() => void)[] = [];

  constructor(
    private readonly transport: UploadTransport,
    private readonly backoffMs: number[] = DEFAULT_BACKOFF_MS,
    private readonly schedule: Schedule = (callback, delay) => void setTimeout(callback, delay),
  ) {}

  enqueue(item: QueueItem): void {
    this.queue.push(item);
    this.notify();
    void this.run();
  }

  get status(): UploaderStatus {
    return {
      pending: this.queue.length,
      pendingBytes: this.queue.reduce(
        (total, item) => total + (item.kind === "chunk" ? item.chunk.samples.length * 2 : 0),
        0,
      ),
      retrying: this.retrying,
      lastErrorCode: this.lastErrorCode,
      lost: [...this.lost],
    };
  }

  subscribe(listener: (status: UploaderStatus) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /** Résout quand la file est vide. */
  whenDrained(): Promise<void> {
    if (this.queue.length === 0) return Promise.resolve();
    return new Promise((resolve) => this.drainWaiters.push(resolve));
  }

  /** Abandon explicite (le praticien termine malgré des envois impossibles). */
  abandon(): QueueItem[] {
    const abandoned = this.queue;
    this.queue = [];
    this.stopped = true;
    this.retrying = false;
    this.notify();
    this.resolveDrain();
    return abandoned;
  }

  private async run(): Promise<void> {
    if (this.running || this.stopped) return;
    this.running = true;
    let attempt = 0;
    while (this.queue.length > 0 && !this.stopped) {
      const item = this.queue[0]!;
      let result: SendResult;
      try {
        result = await this.transport.send(item);
      } catch {
        result = { ok: false, retry: true, code: "NETWORK_UNREACHABLE" };
      }
      if (this.stopped) break;
      if (result.ok) {
        this.queue.shift();
        attempt = 0;
        this.retrying = false;
        this.lastErrorCode = null;
      } else if (result.retry) {
        this.retrying = true;
        this.lastErrorCode = result.code;
        this.notify();
        const delay = this.backoffMs[Math.min(attempt, this.backoffMs.length - 1)] ?? 1000;
        attempt += 1;
        await new Promise<void>((resolve) => this.schedule(resolve, delay));
        continue;
      } else {
        this.queue.shift();
        this.lost.push({ item, code: result.code });
        this.lastErrorCode = result.code;
        attempt = 0;
      }
      this.notify();
    }
    this.running = false;
    if (this.queue.length === 0) this.resolveDrain();
  }

  private resolveDrain(): void {
    const waiters = this.drainWaiters;
    this.drainWaiters = [];
    waiters.forEach((resolve) => resolve());
  }

  private notify(): void {
    const status = this.status;
    this.listeners.forEach((listener) => listener(status));
  }
}
