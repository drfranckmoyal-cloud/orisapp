"use client";

import { useRef, useState } from "react";

import {
  ApiError,
  apiRequest,
  type ClinicalObject,
  type Encounter,
  type SpokenCorrection as Reading,
  sendVoiceCorrection,
} from "@/lib/api";
import { Dictation } from "@/lib/audio/dictation";
import { errorMessage } from "@/lib/labels";

type Message = { tone: "ok" | "error"; text: string };

/** Corriger en dictant ou en écrivant : Oris montre d'abord ce qu'il a compris (§46–47).
 *
 * Rien n'est appliqué sans confirmation : la phrase devient un patch du dossier
 * clinique, jamais une retouche du texte du document.
 */
export function SpokenCorrectionPanel({
  encounter,
  clinicalObject,
  onCorrected,
}: {
  encounter: Encounter;
  clinicalObject: ClinicalObject;
  onCorrected: () => void;
}) {
  const [command, setCommand] = useState("");
  const [reading, setReading] = useState<Reading | null>(null);
  const [message, setMessage] = useState<Message | null>(null);
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const dictation = useRef<Dictation | null>(null);

  function fail(error: unknown) {
    const code = error instanceof ApiError ? error.code : "UNKNOWN";
    setMessage({ tone: "error", text: errorMessage(code) });
  }

  async function read(text: string, apply: boolean) {
    setBusy(true);
    setMessage(null);
    try {
      const result = await apiRequest<Reading>(
        `/encounters/${encounter.id}/corrections/text`,
        {
          method: "POST",
          body: {
            command: text,
            apply,
            ...(apply ? { expected_object_version: clinicalObject.object_version } : {}),
          },
        },
      );
      setReading(result);
      if (result.applied) {
        setCommand("");
        setReading(null);
        setMessage({
          tone: "ok",
          text:
            result.kind === "editorial"
              ? "Préférence de rédaction retenue. Le dossier clinique n’a pas changé."
              : "Correction appliquée : dossier mis à jour, documents réécrits.",
        });
        onCorrected();
      }
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  }

  async function startDictation() {
    setMessage(null);
    const recorder = new Dictation();
    try {
      await recorder.start(() => setRecording(false));
      dictation.current = recorder;
      setRecording(true);
    } catch {
      setMessage({ tone: "error", text: errorMessage("MICROPHONE_UNAVAILABLE") });
    }
  }

  async function stopDictation() {
    const recorder = dictation.current;
    dictation.current = null;
    setRecording(false);
    if (!recorder) return;
    const pcm = recorder.stop();
    if (pcm.length === 0) {
      setMessage({ tone: "error", text: "Rien n’a été entendu." });
      return;
    }
    setBusy(true);
    try {
      const result = await sendVoiceCorrection(encounter.id, pcm);
      setReading(result);
      setCommand("");
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  }

  const correctable = ["review", "validated", "exported"].includes(encounter.status);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <label className="field">
        Dictez ou écrivez votre correction
        <input
          className="input"
          value={command}
          placeholder="Remplace 26 par 27"
          disabled={busy || !correctable}
          onChange={(event) => setCommand(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && command.trim()) void read(command, false);
          }}
        />
      </label>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button
          type="button"
          className="button button-secondary"
          disabled={busy || !command.trim() || !correctable}
          onClick={() => void read(command, false)}
        >
          Voir ce qu’Oris comprend
        </button>
        <button
          type="button"
          className={recording ? "button button-primary" : "button button-secondary"}
          disabled={busy || !correctable}
          onClick={() => (recording ? void stopDictation() : void startDictation())}
        >
          {recording ? "Arrêter la dictée" : "Dicter la correction"}
        </button>
      </div>

      {reading && (
        <div
          className={`banner ${reading.kind === "unclear" ? "banner-review" : "banner-info"}`}
          role="status"
        >
          <strong>{reading.summary}</strong>
          {reading.reason && <div>{reading.reason}</div>}
          {reading.candidates.length > 0 && (
            <ul>
              {reading.candidates.map((candidate) => (
                <li key={candidate}>{candidate}</li>
              ))}
            </ul>
          )}
          {reading.kind !== "unclear" && (
            <div>
              {reading.impact === "high" && (
                <p className="muted">
                  Cette correction touche le dossier clinique : relisez avant d’appliquer.
                </p>
              )}
              <button
                type="button"
                className="button button-primary"
                disabled={busy}
                onClick={() => void read(command || reading.summary, true)}
              >
                {reading.kind === "editorial" ? "Retenir la préférence" : "Appliquer la correction"}
              </button>
            </div>
          )}
        </div>
      )}

      {message && (
        <div
          className={`banner ${message.tone === "ok" ? "banner-info" : "banner-critical"}`}
          role="status"
        >
          {message.text}
        </div>
      )}
    </div>
  );
}
