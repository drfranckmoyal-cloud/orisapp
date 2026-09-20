"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { Carte, EnTetePage, EtatVide, Squelette } from "@/components/ui";
import type { Encounter, TranscriptView } from "@/lib/api";
import { SPEAKER, errorMessage, formatClock, formatDateTime, nomPatient } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

/** La transcription brute, telle qu'elle est sortie de la machine.
 *
 * Elle n'est pas le dossier : le compte rendu s'appuie sur les faits extraits, pas
 * sur ce texte. On la donne parce qu'un praticien doit pouvoir vérifier ce qui a
 * été entendu — pas pour qu'il travaille dessus.
 */
export default function TranscriptionPage() {
  const { id } = useParams<{ id: string }>();
  const [encounter] = useApi<Encounter>(`/encounters/${id}`);
  const [transcript] = useApi<TranscriptView>(`/encounters/${id}/transcript`);

  const segments = transcript.state === "ready" ? transcript.data.segments : [];
  const patient =
    encounter.state === "ready"
      ? nomPatient(encounter.data.patient)
      : "";
  const quand =
    encounter.state === "ready"
      ? formatDateTime(encounter.data.started_at ?? encounter.data.created_at)
      : "";

  return (
    <div className="page">
      <EnTetePage
        surTitre="Transcription brute"
        titre={patient || "Chargement…"}
        action={
          <Link href={`/consultations/${id}`} className="link-button">
            Revenir au compte rendu
          </Link>
        }
      />

      <Carte titre={quand}>
        <p className="muted" style={{ marginTop: 0 }}>
          Ce texte est la sortie de la transcription, sans mise en forme ni relecture.
          <strong> Le compte rendu ne vient pas de lui</strong> : il s’appuie sur les faits
          cliniques extraits, chacun rattaché à la phrase qui l’a produit. Cette page sert
          à vérifier ce qui a été entendu.
        </p>

        {transcript.state === "loading" && <Squelette lignes={6} />}
        {transcript.state === "error" && <EtatVide titre={errorMessage(transcript.code)} />}
        {transcript.state === "ready" && segments.length === 0 && (
          <EtatVide titre="Aucune parole reconnue">
            L’enregistrement n’a rien donné d’exploitable. Le compte rendu n’a pas pu être
            rédigé.
          </EtatVide>
        )}

        {segments.length > 0 && (
          <ul className="liste-simple" style={{ paddingLeft: 0, listStyle: "none", gap: 10 }}>
            {segments.map((segment) => (
              <li key={segment.segment_id} style={{ display: "grid", gap: 2 }}>
                <span className="muted" style={{ fontSize: "var(--texte-xs)" }}>
                  {formatClock(segment.start_ms)} ·{" "}
                  {SPEAKER[segment.speaker_role] ?? segment.speaker_role}
                </span>
                <span style={{ color: "var(--encre)" }}>{segment.text}</span>
              </li>
            ))}
          </ul>
        )}
      </Carte>
    </div>
  );
}
