/** Dictée courte d'une correction : on enregistre, on envoie, on oublie.
 *
 * Rien n'est stocké : l'audio part dans la requête et n'existe nulle part ailleurs.
 */

import { type AudioSource, MicrophoneSource } from "@/lib/audio/sources";
import { Resampler, TARGET_SAMPLE_RATE, level, toInt16 } from "@/lib/audio/pcm";

export const MAX_DICTATION_MS = 20_000;

export class Dictation {
  private source: AudioSource | null = null;
  private resampler: Resampler | null = null;
  private pieces: Int16Array[] = [];

  constructor(private readonly makeSource: () => AudioSource = () => new MicrophoneSource()) {}

  /** `onNiveau` : le volume de la voix (0…1), pour montrer que le micro entend. */
  async start(onEnded: () => void = () => {}, onNiveau?: (niveau: number) => void): Promise<void> {
    this.pieces = [];
    this.resampler = null;
    this.source = this.makeSource();
    await this.source.start((samples, sampleRate) => {
      this.resampler ??= new Resampler(sampleRate);
      onNiveau?.(level(samples));
      const resampled = this.resampler.process(samples);
      if (resampled.length > 0) this.pieces.push(toInt16(resampled));
    }, onEnded);
  }

  /** Arrête le micro et rend le son capté, en PCM 16 kHz mono. */
  stop(): Uint8Array {
    this.source?.stop();
    this.source = null;
    const total = this.pieces.reduce((sum, piece) => sum + piece.length, 0);
    const joined = new Int16Array(Math.min(total, MAX_DICTATION_MS * (TARGET_SAMPLE_RATE / 1000)));
    let offset = 0;
    for (const piece of this.pieces) {
      if (offset >= joined.length) break;
      joined.set(piece.subarray(0, joined.length - offset), offset);
      offset += piece.length;
    }
    this.pieces = [];
    return new Uint8Array(joined.buffer, 0, joined.length * 2);
  }
}
