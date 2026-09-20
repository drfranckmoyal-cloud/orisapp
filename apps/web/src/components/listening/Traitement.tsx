"use client";

import { useEffect, useState } from "react";

import { Etapes, type EtapeEtat } from "@/components/ui";
import { apiRequest, type Progress } from "@/lib/api";

const RYTHME_MS = 900;

/** Écran d'attente (S06) : trois étapes, cochées seulement quand elles sont faites.
 *
 * Rien n'est inventé : chaque étape est lue en base par `/progress`. Pas de
 * pourcentage, pas de barre qui avance toute seule.
 */
export function Traitement({
  encounterId,
  envoiEnCours,
}: {
  encounterId: string;
  envoiEnCours: boolean;
}) {
  const [progress, setProgress] = useState<Progress | null>(null);

  useEffect(() => {
    let vivant = true;
    const timer = setInterval(async () => {
      try {
        const lu = await apiRequest<Progress>(`/encounters/${encounterId}/progress`);
        if (vivant) setProgress(lu);
      } catch {
        // Une lecture ratée n'est pas une erreur de traitement : on réessaiera.
      }
    }, RYTHME_MS);
    return () => {
      vivant = false;
      clearInterval(timer);
    };
  }, [encounterId]);

  function etat(fait: boolean, precedentFait: boolean): EtapeEtat {
    if (fait) return "faite";
    return precedentFait ? "encours" : "attente";
  }

  const transcription = (progress?.transcript_segments ?? 0) > 0;
  const faits = (progress?.facts ?? 0) > 0;
  const documents = (progress?.documents ?? 0) > 0;

  return (
    <div style={{ display: "grid", gap: "var(--espace-6)", justifyItems: "center" }}>
      <p style={{ margin: 0, fontSize: "var(--texte-xl)", fontWeight: 600 }}>
        Oris prépare le dossier…
      </p>
      <Etapes
        etapes={[
          {
            libelle: envoiEnCours
              ? "Envoi des derniers segments"
              : "Finalisation de la transcription",
            etat: etat(transcription, !envoiEnCours),
          },
          { libelle: "Structuration clinique", etat: etat(faits, transcription) },
          { libelle: "Préparation des documents", etat: etat(documents, faits) },
        ]}
      />
      <p className="muted" style={{ margin: 0, textAlign: "center", maxWidth: 420 }}>
        Vous pouvez laisser cet écran : la consultation vous attendra sur l’accueil.
      </p>
    </div>
  );
}
