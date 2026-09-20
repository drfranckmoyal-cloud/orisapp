"use client";

import { useState } from "react";

import { Carte, EtatVide, Onglets, Pastille } from "@/components/ui";
import type {
  ClinicalObject,
  ClinicalObjectView,
  DocumentView,
  LearningEventView,
  TranscriptView,
} from "@/lib/api";
import { fiabiliteDe } from "@/lib/fiabilite";
import { LEARNING_EVENT, correctionDetail, formatDateTime } from "@/lib/labels";

import { FactChips } from "./FactChips";
import { type Selection, SourcePanel } from "./SourcePanel";

type OngletRail = "verifier" | "donnees" | "historique";

const LIBELLES_PROBLEME: Record<string, string> = {
  unsupported_claim: "Phrase sans fait d’appui",
  unknown_fact_id: "Phrase citant un fait inconnu",
  tooth_not_supported: "Dent citée absente des faits",
  performed_not_supported: "« Réalisé » sans acte réalisé",
  fact_not_rendered: "Fait non repris dans le document",
  unrendered_concept: "Élément non reconnu, à rédiger",
  operative_field_missing: "Champ important non dicté",
};

/** Rail de révision (S08) : à vérifier, données cliniques, historique.
 *
 * La source d'une phrase se glisse par-dessus le rail : on ne perd jamais le contexte.
 */
export function RailRevision({
  document,
  clinicalObject,
  versions,
  transcript,
  learning,
  selection,
  onSelect,
  motDe,
}: {
  document: DocumentView | undefined;
  clinicalObject: ClinicalObject;
  versions: ClinicalObjectView["versions"];
  transcript: TranscriptView | null;
  learning: LearningEventView[];
  selection: Selection;
  onSelect: (selection: Selection) => void;
  motDe: (concept: string) => string;
}) {
  const [onglet, setOnglet] = useState<OngletRail>("verifier");
  const problemes = document?.validation_issues ?? [];
  const alertes = clinicalObject.warnings;
  const aVerifier = problemes.length + alertes.length;
  const faitsAVerifier = clinicalObject.facts.filter(
    (fait) => fiabiliteDe(fait, motDe(fait.concept) !== fait.concept).niveau === "a_verifier",
  ).length;

  if (selection !== null && transcript) {
    return (
      <Carte
        titre="D’où vient cette phrase ?"
        action={
          <button type="button" className="link-button" onClick={() => onSelect(null)}>
            fermer
          </button>
        }
      >
        <SourcePanel
          selection={selection}
          clinicalObject={clinicalObject}
          transcript={transcript}
          onClose={() => onSelect(null)}
          motDe={motDe}
        />
      </Carte>
    );
  }

  return (
    <Carte serree>
      <Onglets
        valeur={onglet}
        onChange={setOnglet}
        options={[
          { valeur: "verifier", libelle: `À vérifier${aVerifier ? ` (${aVerifier})` : ""}` },
          { valeur: "donnees", libelle: "Données cliniques" },
          { valeur: "historique", libelle: "Historique" },
        ]}
      />

      {onglet === "verifier" && (
        <div style={{ display: "grid", gap: "var(--espace-3)" }}>
          {aVerifier === 0 && (
            <EtatVide titre="Rien à vérifier">
              Chaque phrase du document s’appuie sur une parole de la consultation.
            </EtatVide>
          )}
          {alertes.map((alerte) => (
            <div key={alerte.code} className="ligne-verif">
              <Pastille ton={alerte.severity === "critical" ? "alerte" : "attention"}>
                {alerte.severity === "critical" ? "critique" : "à vérifier"}
              </Pastille>
              <span>{alerte.message}</span>
            </div>
          ))}
          {problemes.map((probleme, index) => (
            <div key={`${probleme.code}-${index}`} className="ligne-verif">
              <Pastille ton={probleme.severity === "critical" ? "alerte" : "attention"}>
                {probleme.severity === "critical" ? "bloquant" : "à vérifier"}
              </Pastille>
              <span>{LIBELLES_PROBLEME[probleme.code] ?? probleme.code}</span>
            </div>
          ))}
        </div>
      )}

      {onglet === "donnees" && (
        <div style={{ display: "grid", gap: "var(--espace-3)" }}>
          {clinicalObject.facts.length === 0 && <EtatVide titre="Aucun fait clinique" />}
          {clinicalObject.facts.length > 0 && (
            <p className="muted" style={{ margin: 0 }}>
              {faitsAVerifier === 0
                ? `${clinicalObject.facts.length} ${clinicalObject.facts.length > 1 ? "informations relevées" : "information relevée"}, aucune n’appelle de vérification.`
                : `${faitsAVerifier} ${faitsAVerifier > 1 ? "informations sont à vérifier" : "information est à vérifier"} sur ${clinicalObject.facts.length}. Passez la souris sur l’étiquette pour savoir pourquoi.`}
            </p>
          )}
          {clinicalObject.facts.map((fait) => {
            const lecture = fiabiliteDe(fait, motDe(fait.concept) !== fait.concept);
            return (
              <div key={fait.fact_id} style={{ display: "grid", gap: 4 }}>
                <button
                  type="button"
                  className="link-button"
                  style={{ textAlign: "left" }}
                  onClick={() => onSelect({ kind: "fact", factId: fait.fact_id })}
                >
                  <strong>{motDe(fait.concept)}</strong>
                  {typeof fait.value === "string" &&
                  fait.value &&
                  fait.value !== motDe(fait.concept)
                    ? ` : ${fait.value}`
                    : ""}
                </button>
                <span style={{ display: "inline-flex", flexWrap: "wrap", gap: 4 }}>
                  <Pastille ton={lecture.niveau === "fiable" ? "valide" : "attention"}>
                    <span title={lecture.raison}>
                      {lecture.niveau === "fiable" ? "fiable" : "à vérifier"}
                    </span>
                  </Pastille>
                  <FactChips fact={fait} />
                </span>
              </div>
            );
          })}
        </div>
      )}

      {onglet === "historique" && (
        <div style={{ display: "grid", gap: "var(--espace-3)" }}>
          <ul className="liste-simple">
            {versions.map((version) => (
              <li key={version.version}>
                <strong>v{version.version}</strong> —{" "}
                {version.change_kind === "extraction" ? "extraction" : "votre correction"} ·{" "}
                {formatDateTime(version.created_at)}
              </li>
            ))}
          </ul>
          {learning.length > 0 && (
            <>
              <p className="muted" style={{ margin: 0 }}>
                Retenu pour l’apprentissage :
              </p>
              <ul className="liste-simple">
                {learning.map((evenement) => (
                  <li key={evenement.learning_event_id}>
                    {LEARNING_EVENT[evenement.event_type] ?? evenement.event_type}
                    {correctionDetail(evenement) && <> — {correctionDetail(evenement)}</>}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </Carte>
  );
}
