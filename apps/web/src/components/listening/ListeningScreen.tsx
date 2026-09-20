"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";

import { Traitement } from "@/components/listening/Traitement";
import { TranscriptionDirecte } from "@/components/listening/TranscriptionDirecte";
import {
  ApiError,
  apiRequest,
  type AudioSessionView,
  type ClientConfig,
  type Encounter,
  type Mark,
} from "@/lib/api";
import {
  type CaptureApi,
  CaptureController,
  type CaptureSnapshot,
  type FinishOutcome,
} from "@/lib/audio/controller";
import { MicrophoneSource, TestToneSource } from "@/lib/audio/sources";
import { HttpUploadTransport } from "@/lib/audio/transport";
import { errorMessage, formatDuration } from "@/lib/labels";

import styles from "./listening.module.css";

type SourceKind = "microphone" | "test";

function captureApi(encounterId: string): CaptureApi {
  return {
    async start(patientInformed) {
      try {
        await apiRequest(`/encounters/${encounterId}/start`, {
          method: "POST",
          body: { patient_informed: patientInformed },
        });
      } catch (error) {
        throw new Error(
          error instanceof ApiError ? error.code : "START_FAILED",
        );
      }
    },
    async finish({
      finalSequence,
      recordedMs,
      acceptGaps,
    }): Promise<FinishOutcome> {
      try {
        await apiRequest(`/encounters/${encounterId}/finish`, {
          method: "POST",
          body: {
            final_sequence: finalSequence,
            client_recorded_ms: recordedMs,
            accept_gaps: acceptGaps,
          },
        });
        return { status: "finished", missing: [] };
      } catch (error) {
        if (
          error instanceof ApiError &&
          error.code === "AUDIO_CHUNKS_MISSING"
        ) {
          return { status: "chunks_missing", missing: error.details };
        }
        throw new Error(
          error instanceof ApiError ? error.code : "FINISH_FAILED",
        );
      }
    },
  };
}

function useMicrophonePermission(): string {
  const [state, setState] = useState("inconnue");
  useEffect(() => {
    if (!navigator.permissions?.query) return;
    navigator.permissions
      .query({ name: "microphone" as PermissionName })
      .then((status) => {
        setState(status.state);
        status.onchange = () => setState(status.state);
      })
      .catch(() => undefined);
  }, []);
  return state;
}

function subscribeOnline(callback: () => void): () => void {
  window.addEventListener("online", callback);
  window.addEventListener("offline", callback);
  return () => {
    window.removeEventListener("online", callback);
    window.removeEventListener("offline", callback);
  };
}

function useOnline(): boolean {
  return useSyncExternalStore(
    subscribeOnline,
    () => navigator.onLine,
    () => true,
  );
}

const PERMISSION_LABEL: Record<string, string> = {
  granted: "Micro autorisé",
  prompt: "Autorisation du micro demandée au démarrage",
  denied: "Micro refusé par le navigateur",
  inconnue: "Autorisation du micro demandée au démarrage",
};

export function ListeningScreen({
  encounter,
  config,
  audio,
}: {
  encounter: Encounter;
  config: ClientConfig;
  audio: AudioSessionView | null;
}) {
  const router = useRouter();
  const permission = useMicrophonePermission();
  const online = useOnline();
  const [sourceKind, setSourceKind] = useState<SourceKind>("microphone");
  const [informed, setInformed] = useState(false);
  const [snapshot, setSnapshot] = useState<CaptureSnapshot | null>(null);
  const [missing, setMissing] = useState<string[] | null>(null);
  const [finishError, setFinishError] = useState<string | null>(null);
  const [stalled, setStalled] = useState(false);
  const [marks, setMarks] = useState<Mark[]>([]);
  const controllerRef = useRef<CaptureController | null>(null);
  // Lu au moment d'ouvrir la source : un changement de choix après un échec est pris en compte.
  const sourceKindRef = useRef<SourceKind>("microphone");

  function chooseSource(kind: SourceKind) {
    sourceKindRef.current = kind;
    setSourceKind(kind);
  }

  const interrupted =
    snapshot === null &&
    (encounter.status === "recording" || encounter.status === "paused");

  function createController(resumeFrom?: {
    nextSequence: number;
    nextTimestampMs: number;
  }) {
    const controller = new CaptureController({
      api: captureApi(encounter.id),
      transport: new HttpUploadTransport(encounter.id),
      createSource: () =>
        sourceKindRef.current === "test"
          ? new TestToneSource()
          : new MicrophoneSource(),
      maxSessionMs: config.max_session_minutes * 60_000,
      warnSessionMs: config.warn_session_minutes * 60_000,
      ...(resumeFrom ? { resumeFrom } : {}),
    });
    controllerRef.current = controller;
    controller.subscribe((next) => {
      setSnapshot(next);
      if (next.network === "online") setStalled(false);
    });
    return controller;
  }

  // Jamais d'écoute cachée : quitter l'écran met l'écoute en pause.
  useEffect(() => {
    return () => controllerRef.current?.pause();
  }, []);

  useEffect(() => {
    const active =
      snapshot &&
      ["recording", "paused", "microphone_lost", "finishing"].includes(
        snapshot.phase,
      );
    if (!active) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [snapshot]);

  // Connexion absente depuis 15 s : proposer de terminer malgré tout.
  useEffect(() => {
    if (snapshot?.network !== "reconnecting") return;
    const timer = setTimeout(() => setStalled(true), 15_000);
    return () => clearTimeout(timer);
  }, [snapshot?.network]);

  // « Marquer un point » (§11) : un signet sur l'instant écouté, rien de clinique.
  async function markMoment() {
    const recordedMs = controllerRef.current?.state.recordedMs ?? snapshot?.recordedMs ?? 0;
    try {
      const mark = await apiRequest<Mark>(`/encounters/${encounter.id}/marks`, {
        method: "POST",
        body: { timestamp_ms: Math.round(recordedMs) },
      });
      setMarks((current) =>
        current.some((item) => item.timestamp_ms === mark.timestamp_ms)
          ? current
          : [...current, mark],
      );
    } catch {
      // Un repère raté ne doit jamais interrompre l'écoute : on n'en parle pas ici.
    }
  }

  async function finish(acceptGaps: boolean) {
    const controller = controllerRef.current;
    if (!controller) return;
    setFinishError(null);
    try {
      const outcome = await controller.finish(acceptGaps);
      if (outcome.status === "chunks_missing") {
        setMissing(outcome.missing);
        return;
      }
      router.push(`/consultations/${encounter.id}`);
    } catch (error) {
      setFinishError(
        errorMessage(error instanceof Error ? error.message : "FINISH_FAILED"),
      );
    }
  }

  async function resumeInterrupted() {
    const controller = createController({
      nextSequence: audio?.next_sequence ?? 0,
      nextTimestampMs: audio?.next_timestamp_ms ?? 0,
    });
    const last = audio?.last_received_at
      ? Date.parse(audio.last_received_at)
      : null;
    const interruptionMs =
      last === null ? null : Math.max(0, Date.now() - last);
    await controller.resumeAfterReload(
      interruptionMs,
      encounter.status === "paused",
    );
  }

  async function finishInterrupted() {
    try {
      if (encounter.status === "recording") {
        await apiRequest(`/encounters/${encounter.id}/audio/gaps`, {
          method: "POST",
          body: { reason: "page_reloaded", duration_ms: null },
        });
      }
      await apiRequest(`/encounters/${encounter.id}/finish`, {
        method: "POST",
        body: { accept_gaps: true },
      });
      router.push(`/consultations/${encounter.id}`);
    } catch (error) {
      setFinishError(
        errorMessage(error instanceof ApiError ? error.code : "FINISH_FAILED"),
      );
    }
  }

  const stalledLong = stalled && snapshot?.network === "reconnecting";
  const phase = snapshot?.phase ?? "ready";
  const name = `${encounter.patient.first_name} ${encounter.patient.last_name}`;

  const sourceChoice = config.test_audio_source_enabled ? (
    <fieldset
      className={styles.choices}
      style={{ border: "none", padding: 0, margin: 0 }}
    >
      <legend className="muted">Source du son</legend>
      <label className={styles.choice}>
        <input
          type="radio"
          checked={sourceKind === "microphone"}
          onChange={() => chooseSource("microphone")}
        />
        Micro de l’ordinateur
      </label>
      <label className={styles.choice}>
        <input
          type="radio"
          checked={sourceKind === "test"}
          onChange={() => chooseSource("test")}
        />
        Son de test, sans micro (développement uniquement)
      </label>
    </fieldset>
  ) : null;

  // --- Écoute interrompue par un rechargement -------------------------------------
  if (interrupted) {
    return (
      <div className={styles.card}>
        <h1>{name}</h1>
        <div className="banner banner-critical" role="alert">
          L’écoute a été interrompue (page fermée ou rechargée).
          {encounter.status === "recording" &&
            " La partie non captée sera signalée comme manquante."}
        </div>
        <p className="muted">
          {audio
            ? `${formatDuration(audio.received_duration_ms)} d’audio déjà reçus par le serveur.`
            : null}
        </p>
        {sourceChoice}
        <div className={styles.actions}>
          <button
            type="button"
            className="button button-large"
            onClick={resumeInterrupted}
          >
            Reprendre l’écoute
          </button>
          <button
            type="button"
            className="button button-secondary"
            onClick={finishInterrupted}
          >
            Terminer la consultation
          </button>
        </div>
        {finishError && (
          <div className="banner banner-critical">{finishError}</div>
        )}
      </div>
    );
  }

  // --- Pré-écran (S03) --------------------------------------------------------------
  if (
    phase === "ready" ||
    phase === "starting" ||
    (phase === "error" && snapshot?.errorCode)
  ) {
    const needsInformation = config.patient_information_mode === "confirm";
    return (
      <div className={styles.card}>
        <div>
          <p className="subtitle">Nouvelle consultation</p>
          <h1>{name}</h1>
        </div>
        <div className={styles.statusRow}>
          <div
            className={styles.status}
            data-tone={permission === "denied" ? "critical" : undefined}
          >
            🎙{" "}
            {sourceKind === "test"
              ? "Son de test (sans micro)"
              : (PERMISSION_LABEL[permission] ?? PERMISSION_LABEL.inconnue)}
          </div>
          <div
            className={styles.status}
            data-tone={online ? undefined : "critical"}
          >
            {online ? "Connexion au serveur disponible" : "Hors connexion"}
          </div>
        </div>
        {sourceChoice}
        {needsInformation && (
          <label className={styles.choice}>
            <input
              type="checkbox"
              checked={informed}
              onChange={(event) => setInformed(event.target.checked)}
            />
            Le patient a été informé de l’enregistrement de la consultation.
          </label>
        )}
        {snapshot?.errorCode && (
          <div className="banner banner-critical" role="alert">
            {errorMessage(snapshot.errorCode)}
          </div>
        )}
        <div className={styles.actions}>
          <button
            type="button"
            className="button button-large"
            disabled={phase === "starting" || (needsInformation && !informed)}
            onClick={() =>
              void (controllerRef.current ?? createController()).start(informed)
            }
          >
            {phase === "starting" ? "Démarrage…" : "Commencer l’écoute"}
          </button>
        </div>
      </div>
    );
  }

  // --- Écoute active (S05) et fin -----------------------------------------------------
  const state = snapshot!;
  const enAttente = state.phase === "finishing" || state.phase === "finished";
  const labels: Record<string, string> = {
    recording: "Écoute en cours",
    paused: "En pause — micro coupé",
    microphone_lost: "Micro perdu",
    finishing:
      state.pendingUploads > 0
        ? "Envoi des derniers segments…"
        : "Oris prépare le dossier…",
    finished: "Oris prépare le dossier…",
    error: "Erreur",
  };
  const indicator =
    state.phase === "recording"
      ? "recording"
      : state.phase === "microphone_lost"
        ? "alert"
        : "idle";

  return (
    <div className={styles.card}>
      {!enAttente && (
        <div className={styles.center}>
          <p className="muted" style={{ margin: 0 }}>
            {name}
          </p>
          <div
            className={styles.indicator}
            data-state={indicator}
            aria-hidden="true"
          >
            {state.phase === "microphone_lost" ? (
              <span style={{ fontSize: 44, fontWeight: 600 }}>!</span>
            ) : (
              <Image
                src="/oris-symbole.png"
                alt=""
                width={368}
                height={365}
                className={styles.symbole}
                style={{ opacity: state.phase === "recording" ? 1 : 0.4 }}
                priority
              />
            )}
          </div>
          <p className={styles.stateLabel} role="status" aria-live="polite">
            {labels[state.phase] ?? state.phase}
          </p>
          <p className={styles.timer} aria-label="Durée écoutée">
            {formatDuration(state.recordedMs)}
          </p>
          <div className={styles.meter} aria-hidden="true">
            <div
              className={styles.meterFill}
              style={{ width: `${Math.round(state.level * 100)}%` }}
            />
          </div>
        </div>
      )}

      {!enAttente && (
        <div className={styles.statusRow}>
          <div
            className={styles.status}
            data-tone={
              state.phase === "microphone_lost" ? "critical" : undefined
            }
          >
            {state.phase === "recording"
              ? "Micro actif"
              : state.phase === "microphone_lost"
                ? "Micro coupé ou débranché"
                : "Micro coupé"}
          </div>
          <div
            className={styles.status}
            data-tone={state.network === "reconnecting" ? "warning" : undefined}
          >
            {state.network === "reconnecting"
              ? `Connexion interrompue — ${state.pendingUploads} envoi(s) en attente`
              : state.pendingUploads > 1
                ? `Envoi en cours (${state.pendingUploads})`
                : "Audio envoyé au serveur"}
          </div>
        </div>
      )}

      {state.phase === "microphone_lost" && (
        <div className="banner banner-critical" role="alert">
          {errorMessage("microphone_lost")}
        </div>
      )}
      {state.lostUploads > 0 && (
        <div className="banner banner-critical" role="alert">
          {state.lostUploads} segment(s) audio refusé(s) par le serveur : ils
          seront signalés comme manquants.
        </div>
      )}
      {state.maxDurationReached ? (
        <div className="banner banner-review">
          Durée maximale de {config.max_session_minutes} minutes atteinte :
          l’écoute est en pause. Terminez la consultation.
        </div>
      ) : (
        state.warnDurationReached && (
          <div className="banner banner-review">
            L’écoute approche de la durée maximale ({config.max_session_minutes}{" "}
            minutes).
          </div>
        )
      )}

      {state.phase === "finishing" || state.phase === "finished" ? (
        <div className={styles.center}>
          <Traitement
            encounterId={encounter.id}
            envoiEnCours={state.pendingUploads > 0}
          />
          {(stalledLong || missing) && (
            <div className="banner banner-review" style={{ textAlign: "left" }}>
              {missing
                ? `${missing.length} segment(s) audio ne sont pas arrivés au serveur.`
                : "La connexion ne revient pas : les derniers segments ne peuvent pas être envoyés."}{" "}
              Vous pouvez attendre, ou terminer malgré tout : la partie
              manquante sera signalée par une alerte critique et le compte rendu
              ne sera pas présenté comme complet.
              <div>
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={() => void finish(true)}
                >
                  Terminer malgré tout
                </button>
              </div>
            </div>
          )}
          {finishError && (
            <div className="banner banner-critical">{finishError}</div>
          )}
        </div>
      ) : (
        <div className={styles.actions}>
          {state.phase === "recording" ? (
            <button
              type="button"
              className="button button-secondary"
              onClick={() => controllerRef.current?.pause()}
            >
              Pause
            </button>
          ) : (
            <button
              type="button"
              className="button button-secondary"
              disabled={state.maxDurationReached}
              onClick={() => void controllerRef.current?.resume()}
            >
              Reprendre
            </button>
          )}
          <button
            type="button"
            className="button button-secondary"
            onClick={() => void markMoment()}
          >
            Marquer un point
          </button>
          <button
            type="button"
            className="button button-primary"
            onClick={() => void finish(false)}
          >
            Terminer
          </button>
        </div>
      )}
      {!enAttente && <TranscriptionDirecte encounterId={encounter.id} />}
      {marks.length > 0 && !enAttente && (
        <p className="muted" style={{ margin: 0, textAlign: "center" }} role="status">
          {marks.length === 1 ? "1 point marqué" : `${marks.length} points marqués`} :{" "}
          {marks.map((mark) => formatDuration(mark.timestamp_ms)).join(", ")}. Vous les
          retrouverez à la relecture.
        </p>
      )}
      {state.errorCode && state.phase !== "microphone_lost" && (
        <div className="banner banner-critical">
          {errorMessage(state.errorCode)}
        </div>
      )}
    </div>
  );
}
