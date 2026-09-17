/** Sources de son : micro réel, ou source de test sans micro (développement). */

export type CaptureErrorCode =
  | "insecure_context"
  | "unsupported"
  | "permission_denied"
  | "no_microphone"
  | "microphone_busy"
  | "capture_failed";

export class CaptureError extends Error {
  constructor(readonly code: CaptureErrorCode) {
    super(code);
  }
}

export interface AudioSource {
  /** `onEnded` : la source s'est arrêtée d'elle-même (micro débranché, retiré). */
  start(onSamples: (samples: Float32Array, sampleRate: number) => void, onEnded: () => void): Promise<void>;
  stop(): void;
}

export class MicrophoneSource implements AudioSource {
  private stream: MediaStream | null = null;
  private context: AudioContext | null = null;

  async start(
    onSamples: (samples: Float32Array, sampleRate: number) => void,
    onEnded: () => void,
  ): Promise<void> {
    if (typeof window === "undefined" || !window.isSecureContext) {
      throw new CaptureError("insecure_context");
    }
    if (!navigator.mediaDevices?.getUserMedia || typeof AudioWorkletNode === "undefined") {
      throw new CaptureError("unsupported");
    }
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
    } catch (error) {
      const name = error instanceof DOMException ? error.name : "";
      if (name === "NotAllowedError" || name === "SecurityError") throw new CaptureError("permission_denied");
      if (name === "NotFoundError" || name === "OverconstrainedError") throw new CaptureError("no_microphone");
      if (name === "NotReadableError") throw new CaptureError("microphone_busy");
      throw new CaptureError("capture_failed");
    }
    try {
      this.context = new AudioContext();
      await this.context.audioWorklet.addModule("/pcm-capture-worklet.js");
      const input = this.context.createMediaStreamSource(this.stream);
      const node = new AudioWorkletNode(this.context, "pcm-capture");
      const sampleRate = this.context.sampleRate;
      node.port.onmessage = (event: MessageEvent<Float32Array>) => onSamples(event.data, sampleRate);
      input.connect(node);
      for (const track of this.stream.getAudioTracks()) {
        track.addEventListener("ended", onEnded);
      }
    } catch {
      this.stop();
      throw new CaptureError("capture_failed");
    }
  }

  stop(): void {
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    void this.context?.close();
    this.context = null;
  }
}

/**
 * Source de test : produit un son faible et régulier, sans micro.
 * Réservée au développement local (consultations fictives, navigateur sans micro).
 */
export class TestToneSource implements AudioSource {
  private timer: ReturnType<typeof setInterval> | null = null;
  private phase = 0;

  constructor(
    private readonly intervalMs = 100,
    private readonly sampleRate = 16_000,
  ) {}

  async start(onSamples: (samples: Float32Array, sampleRate: number) => void): Promise<void> {
    const blockSize = Math.round((this.sampleRate * this.intervalMs) / 1000);
    this.timer = setInterval(() => {
      const block = new Float32Array(blockSize);
      for (let i = 0; i < blockSize; i++) {
        block[i] = 0.05 * Math.sin(this.phase);
        this.phase += (2 * Math.PI * 220) / this.sampleRate;
      }
      onSamples(block, this.sampleRate);
    }, this.intervalMs);
  }

  stop(): void {
    if (this.timer !== null) clearInterval(this.timer);
    this.timer = null;
  }
}
