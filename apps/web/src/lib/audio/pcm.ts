/** Conversion du son capté en PCM 16 kHz mono 16 bits (format attendu par l'API). */

export const TARGET_SAMPLE_RATE = 16_000;
export const SAMPLES_PER_MS = TARGET_SAMPLE_RATE / 1000;

/**
 * Rééchantillonneur par moyenne, avec état : les blocs successifs se raccordent
 * sans perte ni doublon d'échantillon. Suffisant pour la parole (bande < 8 kHz).
 */
export class Resampler {
  private readonly ratio: number;
  private carry: number[] = [];
  private position = 0;

  constructor(
    readonly inputRate: number,
    readonly outputRate: number = TARGET_SAMPLE_RATE,
  ) {
    if (inputRate < outputRate) {
      throw new Error("Fréquence d'entrée inférieure à 16 kHz non prise en charge");
    }
    this.ratio = inputRate / outputRate;
  }

  process(input: Float32Array): Float32Array {
    if (this.ratio === 1) return input.slice();
    const samples = this.carry.length ? Float32Array.from([...this.carry, ...input]) : input;
    const output: number[] = [];
    let position = this.position;
    while (position + this.ratio <= samples.length) {
      const start = Math.floor(position);
      const end = Math.floor(position + this.ratio);
      let sum = 0;
      for (let i = start; i < end; i++) sum += samples[i] ?? 0;
      output.push(sum / Math.max(1, end - start));
      position += this.ratio;
    }
    const consumed = Math.floor(position);
    this.carry = Array.from(samples.subarray(consumed));
    this.position = position - consumed;
    return Float32Array.from(output);
  }
}

export function toInt16(samples: Float32Array): Int16Array {
  const output = new Int16Array(samples.length);
  for (let i = 0; i < samples.length; i++) {
    const clamped = Math.max(-1, Math.min(1, samples[i] ?? 0));
    output[i] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
  }
  return output;
}

/** Niveau sonore (0 à 1) pour l'indicateur d'activité vocale. */
export function level(samples: Float32Array): number {
  if (samples.length === 0) return 0;
  let sum = 0;
  for (const sample of samples) sum += sample * sample;
  return Math.min(1, Math.sqrt(sum / samples.length) * 4);
}

/** Octets little-endian, quel que soit le processeur. */
export function int16ToBytes(samples: Int16Array): Uint8Array {
  const bytes = new Uint8Array(samples.length * 2);
  const view = new DataView(bytes.buffer);
  samples.forEach((sample, index) => view.setInt16(index * 2, sample, true));
  return bytes;
}
