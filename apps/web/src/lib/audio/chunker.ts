/** Découpe du flux en segments numérotés et horodatés à l'échantillon près. */

import { SAMPLES_PER_MS, TARGET_SAMPLE_RATE } from "./pcm";

export const CHUNK_SAMPLES = 2 * TARGET_SAMPLE_RATE; // 2 s

export interface PcmChunk {
  sequence: number;
  /** Début du segment en temps écouté (pauses exclues), en ms. */
  timestampMs: number;
  durationMs: number;
  samples: Int16Array;
}

export class Chunker {
  private buffer: Int16Array;
  private filled = 0;
  private nextSequence: number;
  private sampleOffset: number;

  constructor(
    readonly chunkSamples = CHUNK_SAMPLES,
    startSequence = 0,
    startTimestampMs = 0,
  ) {
    this.buffer = new Int16Array(chunkSamples);
    this.nextSequence = startSequence;
    this.sampleOffset = Math.round(startTimestampMs * SAMPLES_PER_MS);
  }

  /** Temps écouté total, segment en cours compris. */
  get recordedMs(): number {
    return Math.floor((this.sampleOffset + this.filled) / SAMPLES_PER_MS);
  }

  /** Dernier numéro de segment émis (-1 si aucun). */
  get lastSequence(): number {
    return this.nextSequence - 1;
  }

  push(samples: Int16Array): PcmChunk[] {
    const chunks: PcmChunk[] = [];
    let offset = 0;
    while (offset < samples.length) {
      const take = Math.min(this.chunkSamples - this.filled, samples.length - offset);
      this.buffer.set(samples.subarray(offset, offset + take), this.filled);
      this.filled += take;
      offset += take;
      if (this.filled === this.chunkSamples) {
        chunks.push(this.emit());
      }
    }
    return chunks;
  }

  /** Émet le segment partiel en cours (pause, fin d'écoute). */
  flush(): PcmChunk | null {
    return this.filled > 0 ? this.emit() : null;
  }

  private emit(): PcmChunk {
    const chunk: PcmChunk = {
      sequence: this.nextSequence,
      timestampMs: Math.floor(this.sampleOffset / SAMPLES_PER_MS),
      durationMs: Math.round(this.filled / SAMPLES_PER_MS),
      samples: this.buffer.slice(0, this.filled),
    };
    this.nextSequence += 1;
    this.sampleOffset += this.filled;
    this.filled = 0;
    return chunk;
  }
}
