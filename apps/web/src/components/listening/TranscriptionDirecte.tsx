"use client";

import { useEffect, useRef, useState } from "react";

import { apiRequest, type LiveTranscript } from "@/lib/api";
import { SPEAKER } from "@/lib/labels";

import styles from "./listening.module.css";

const INTERVALLE_MS = 1200;

/** Panneau « ce qu'Oris entend », replié par défaut (§11).
 *
 * Il sert à une seule chose : voir que le micro capte et que les mots tombent juste.
 * Ce texte n'est **pas** le compte rendu — la transcription du dossier est refaite
 * après la consultation, sur l'enregistrement complet (§14.1). Le panneau le dit,
 * pour qu'on ne puisse pas s'y tromper.
 */
export function TranscriptionDirecte({ encounterId }: { encounterId: string }) {
  const [ouvert, setOuvert] = useState(false);
  const [vue, setVue] = useState<LiveTranscript | null>(null);
  const fin = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let vivant = true;
    async function lire() {
      try {
        const suite = await apiRequest<LiveTranscript>(`/encounters/${encounterId}/live`);
        if (vivant) setVue(suite);
      } catch {
        // Le direct est un confort : son échec ne s'affiche pas en alarme.
      }
    }
    void lire();
    // Tant que le panneau est fermé, on interroge quand même : le libellé du bouton
    // doit pouvoir dire qu'Oris n'entend rien, sans qu'on ait à l'ouvrir.
    const minuteur = setInterval(() => void lire(), ouvert ? INTERVALLE_MS : INTERVALLE_MS * 4);
    return () => {
      vivant = false;
      clearInterval(minuteur);
    };
  }, [encounterId, ouvert]);

  useEffect(() => {
    if (!ouvert) return;
    // Tous les environnements n'ont pas scrollIntoView : ne jamais faire tomber
    // l'écran d'écoute pour un défilement de confort.
    fin.current?.scrollIntoView?.({ block: "end" });
  }, [ouvert, vue]);

  if (!vue || vue.state === "disabled") return null;

  const muet = vue.state === "running" && vue.total === 0;
  const resume =
    vue.state === "failed"
      ? "l’écoute en direct s’est interrompue"
      : muet
        ? "rien d’entendu pour l’instant"
        : `${vue.total} ${vue.total > 1 ? "paroles entendues" : "parole entendue"}`;

  return (
    <div className={styles.direct}>
      <button
        type="button"
        className="link-button"
        aria-expanded={ouvert}
        onClick={() => setOuvert((etat) => !etat)}
      >
        {ouvert ? "▾" : "▸"} Ce qu’Oris entend — {resume}
      </button>

      {ouvert && (
        <div className={styles.directCorps}>
          <p className="muted" style={{ margin: 0 }}>
            Texte provisoire, pour vérifier que le micro capte. Le compte rendu sera
            rédigé après la consultation, à partir de l’enregistrement complet.
          </p>
          {vue.state === "failed" && (
            <p className="muted" style={{ margin: 0 }}>
              L’affichage en direct s’est arrêté. <strong>L’enregistrement continue</strong>{" "}
              et le compte rendu ne sera pas affecté.
            </p>
          )}
          {vue.reconnections > 0 && (
            <p className="muted" style={{ margin: 0 }}>
              {vue.reconnections} reconnexion(s) — quelques mots peuvent apparaître deux
              fois ci-dessous.
            </p>
          )}
          <div className={styles.directLignes}>
            {vue.segments.map((segment) => (
              <p
                key={segment.segment_id}
                className={segment.is_final ? styles.directFinal : styles.directProvisoire}
              >
                <span className="muted">
                  {SPEAKER[segment.speaker_role] ?? segment.speaker_role} —{" "}
                </span>
                {segment.text}
              </p>
            ))}
            <div ref={fin} />
          </div>
        </div>
      )}
    </div>
  );
}
