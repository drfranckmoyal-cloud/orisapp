/** Envoi HTTP vers l'API Oris des éléments de la file de capture. */

import { API_BASE_URL } from "../api";
import { sha256Hex } from "./checksum";
import { int16ToBytes } from "./pcm";
import type { QueueItem, SendResult, UploadTransport } from "./uploader";

export const AUDIO_FORMAT = "audio/pcm;rate=16000;channels=1;encoding=s16le";

/** Codes d'erreur qu'un nouvel essai ne peut pas corriger. */
const PERMANENT = new Set(["CHUNK_CONFLICT", "ENCOUNTER_NOT_RECORDING", "CHUNK_TOO_LARGE", "UNSUPPORTED_AUDIO_FORMAT", "INVALID_CHUNK", "ENCOUNTER_NOT_FOUND"]);

export async function interpret(response: Response): Promise<SendResult> {
  if (response.ok) return { ok: true };
  const body = (await response.json().catch(() => ({}))) as { code?: string };
  const code = body.code ?? `HTTP_${response.status}`;
  // Pause ou reprise déjà appliquée (réponse perdue puis renvoi) : état atteint.
  if (code === "INVALID_TRANSITION") return { ok: true };
  const retry = response.status >= 500 || response.status === 408 || response.status === 429 || !PERMANENT.has(code);
  return { ok: false, retry, code };
}

export class HttpUploadTransport implements UploadTransport {
  constructor(
    private readonly encounterId: string,
    private readonly fetcher: typeof fetch = (...args) => fetch(...args),
    private readonly baseUrl: string = API_BASE_URL,
  ) {}

  async send(item: QueueItem): Promise<SendResult> {
    const root = `${this.baseUrl}/encounters/${this.encounterId}`;
    let response: Response;
    switch (item.kind) {
      case "chunk": {
        const bytes = int16ToBytes(item.chunk.samples);
        response = await this.fetcher(`${root}/audio/chunks/${item.chunk.sequence}`, {
          method: "PUT",
          headers: {
            "Content-Type": AUDIO_FORMAT,
            "X-Chunk-Timestamp-Ms": String(item.chunk.timestampMs),
            "X-Chunk-Checksum": await sha256Hex(bytes),
          },
          body: bytes as BodyInit,
        });
        break;
      }
      case "pause":
      case "resume":
        response = await this.fetcher(`${root}/${item.kind}`, { method: "POST" });
        break;
      case "gap":
        response = await this.fetcher(`${root}/audio/gaps`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reason: item.reason, duration_ms: item.durationMs }),
        });
        break;
    }
    return interpret(response);
  }
}
