"use client";

import { useParams } from "next/navigation";
import { useState } from "react";

import { CorrectionPanel } from "@/components/review/CorrectionPanel";
import { DocumentBody } from "@/components/review/DocumentView";
import { FactChips } from "@/components/review/FactChips";
import styles from "@/components/review/review.module.css";
import { type Selection, SourcePanel } from "@/components/review/SourcePanel";
import {
  ApiError,
  apiRequest,
  type ClinicalObjectView,
  type DocumentView,
  type Encounter,
  type LearningEventView,
  type TranscriptView,
} from "@/lib/api";
import {
  DOCUMENT_STATUS,
  DOCUMENT_TYPE,
  ENCOUNTER_STATUS,
  LEARNING_EVENT,
  errorMessage,
  formatDateTime,
} from "@/lib/labels";
import { useApi } from "@/lib/useApi";

const ISSUE_LABELS: Record<string, string> = {
  unsupported_claim: "Phrase sans fait d’appui",
  unknown_fact_id: "Phrase citant un fait inconnu",
  tooth_not_supported: "Dent citée absente des faits",
  performed_not_supported: "« Réalisé » sans acte réalisé",
  fact_not_rendered: "Fait non repris dans le document",
  unrendered_concept: "Élément non reconnu à rédiger",
};

function statusChipClass(status: DocumentView["status"]): string {
  if (status === "validated") return "chip chip-success";
  if (status === "outdated" || status === "needs_review") return "chip chip-review";
  return "chip";
}

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const [encounter, reloadEncounter] = useApi<Encounter>(`/encounters/${id}`);
  const [documents, reloadDocuments] = useApi<DocumentView[]>(`/encounters/${id}/documents`);
  const [clinical, reloadClinical] = useApi<ClinicalObjectView>(`/encounters/${id}/clinical-object`);
  const [transcript] = useApi<TranscriptView>(`/encounters/${id}/transcript`);
  const [learning, reloadLearning] = useApi<LearningEventView[]>(`/encounters/${id}/learning-events`);

  const [activeType, setActiveType] = useState<DocumentView["document_type"]>("consultation_note");
  const [selection, setSelection] = useState<Selection>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [feedback, setFeedback] = useState<{ tone: "ok" | "error"; text: string } | null>(null);

  function reloadAll() {
    reloadEncounter();
    reloadDocuments();
    reloadClinical();
    reloadLearning();
    setSelection(null);
  }

  async function act(path: string, body: unknown, success: string) {
    setFeedback(null);
    try {
      await apiRequest(path, { method: "POST", body });
      setFeedback({ tone: "ok", text: success });
      reloadAll();
    } catch (error) {
      const code = error instanceof ApiError ? error.code : "UNKNOWN";
      setFeedback({ tone: "error", text: errorMessage(code) });
    }
  }

  if (encounter.state === "error") {
    return <p className="muted">{errorMessage(encounter.code)}</p>;
  }
  if (encounter.state !== "ready") {
    return <p className="muted">Chargement…</p>;
  }
  const data = encounter.data;
  const docs = documents.state === "ready" ? documents.data : [];
  const active = docs.find((doc) => doc.document_type === activeType) ?? docs[0];
  const object = clinical.state === "ready" ? clinical.data.clinical_object : null;
  const criticalWarnings = object?.warnings.filter((warning) => warning.severity === "critical") ?? [];
  const allValidated = docs.length > 0 && docs.filter((d) => d.status !== "superseded").every((d) => d.status === "validated");

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="subtitle">
            Consultation du {formatDateTime(data.started_at ?? data.created_at)}
            {data.synthetic_case_id && ` · cas fictif ${data.synthetic_case_id}`}
          </p>
          <h1>
            {data.patient.first_name} {data.patient.last_name}
          </h1>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <span className="chip">{ENCOUNTER_STATUS[data.status]}</span>
          <span className="chip">Dossier clinique v{data.object_version}</span>
          <button
            type="button"
            className="button button-primary"
            disabled={!allValidated || data.status !== "review"}
            onClick={() => act(`/encounters/${id}/validate`, undefined, "Consultation validée.")}
          >
            Valider la consultation
          </button>
        </div>
      </header>

      {data.processing_errors.length > 0 && (
        <div className="banner banner-critical" role="alert">
          Oris a refusé le résultat de l’extraction plutôt que de le corriger en silence :
          {" "}
          {data.processing_errors.map((e) => `${e.rule} (${e.subject_id})`).join(", ")}.
        </div>
      )}
      {criticalWarnings.map((warning) => (
        <div key={warning.code} className="banner banner-critical" role="alert">
          <strong>Alerte critique</strong> — {warning.message} Le compte rendu ne peut pas être
          considéré comme exhaustif.
        </div>
      ))}
      {feedback && (
        <div className={`banner ${feedback.tone === "ok" ? "banner-info" : "banner-critical"}`} role="status">
          {feedback.text}
        </div>
      )}

      <div className={styles.layout}>
        <section className="card" aria-label="Documents">
          {docs.length === 0 && <p className="muted">Aucun document pour cette consultation.</p>}
          {docs.length > 0 && active && (
            <>
              <div className={styles.tabs} role="tablist">
                {docs.map((doc) => (
                  <button
                    key={doc.id}
                    type="button"
                    role="tab"
                    aria-selected={doc.id === active.id}
                    className={styles.tab}
                    onClick={() => {
                      setActiveType(doc.document_type);
                      setSelection(null);
                    }}
                  >
                    {DOCUMENT_TYPE[doc.document_type]}
                  </button>
                ))}
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                <span className={statusChipClass(active.status)}>{DOCUMENT_STATUS[active.status]}</span>
                <span className="muted">
                  Version {active.version} · rédigé depuis le dossier clinique v
                  {active.generated_from_object_version}
                </span>
              </div>

              {!active.is_current && (
                <div className="banner banner-review">
                  Ce document a été rédigé avant la dernière correction du dossier clinique.
                  <div>
                    <button
                      type="button"
                      className="button button-secondary"
                      onClick={() =>
                        act(`/encounters/${id}/documents/generate`, undefined, "Documents régénérés.")
                      }
                    >
                      Régénérer les documents
                    </button>
                  </div>
                </div>
              )}

              <DocumentBody
                document={active}
                selected={selection?.kind === "claim" ? selection.claim : null}
                onSelect={(claim) => setSelection({ kind: "claim", claim })}
              />

              {active.status !== "validated" && active.status !== "superseded" && (
                <div style={{ display: "grid", gap: 12, borderTop: "1px solid var(--color-cloud)", paddingTop: 16 }}>
                  {criticalWarnings.length > 0 && (
                    <label style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
                      <input
                        type="checkbox"
                        checked={acknowledged}
                        onChange={(event) => setAcknowledged(event.target.checked)}
                        style={{ width: 20, height: 20 }}
                      />
                      J’ai pris connaissance de l’alerte critique : ce document n’est pas exhaustif.
                    </label>
                  )}
                  <div>
                    <button
                      type="button"
                      className="button button-primary"
                      disabled={!active.is_current || (criticalWarnings.length > 0 && !acknowledged)}
                      onClick={() =>
                        act(
                          `/documents/${active.id}/validate`,
                          { acknowledged_warning_codes: acknowledged ? criticalWarnings.map((w) => w.code) : [] },
                          `${DOCUMENT_TYPE[active.document_type]} validé.`,
                        )
                      }
                    >
                      Valider ce document
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </section>

        <aside className={styles.side}>
          <section className="card" aria-labelledby="source-heading">
            <h2 id="source-heading">Source</h2>
            {object && transcript.state === "ready" ? (
              <SourcePanel
                selection={selection}
                clinicalObject={object}
                transcript={transcript.data}
                onClose={() => setSelection(null)}
              />
            ) : (
              <p className="muted">Chargement…</p>
            )}
          </section>

          {active && active.validation_issues.length > 0 && (
            <section className="card" aria-labelledby="check-heading">
              <h2 id="check-heading">À vérifier ({active.validation_issues.length})</h2>
              <ul>
                {active.validation_issues.map((issue, index) => (
                  <li key={index}>
                    {ISSUE_LABELS[issue.code] ?? issue.code}
                    {issue.severity === "critical" && " — bloque la validation"}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {object && (
            <section className="card" aria-labelledby="facts-heading">
              <h2 id="facts-heading">Faits cliniques ({object.facts.length})</h2>
              <ul className={styles.factList}>
                {object.facts.map((fact) => (
                  <li key={fact.fact_id} style={{ display: "grid", gap: 4 }}>
                    <button
                      type="button"
                      className="link-button"
                      style={{ textAlign: "left" }}
                      onClick={() => setSelection({ kind: "fact", factId: fact.fact_id })}
                    >
                      {fact.concept}
                      {typeof fact.value === "string" && fact.value !== fact.concept ? ` : ${fact.value}` : ""}
                    </button>
                    <FactChips fact={fact} />
                  </li>
                ))}
              </ul>
            </section>
          )}

          {object && (
            <section className="card" aria-labelledby="correct-heading">
              <h2 id="correct-heading">Corriger</h2>
              <p className="muted">
                Une correction modifie d’abord le dossier clinique ; Oris réécrit ensuite les
                documents.
              </p>
              <CorrectionPanel encounter={data} clinicalObject={object} onCorrected={reloadAll} />
            </section>
          )}

          <section className="card" aria-labelledby="history-heading">
            <h2 id="history-heading">Historique</h2>
            {clinical.state === "ready" && (
              <ul>
                {clinical.data.versions.map((version) => (
                  <li key={version.version}>
                    v{version.version} — {version.change_kind === "extraction" ? "extraction" : "correction du praticien"} ·{" "}
                    {formatDateTime(version.created_at)}
                  </li>
                ))}
              </ul>
            )}
            {learning.state === "ready" && learning.data.length > 0 && (
              <>
                <p className="muted">Enregistré pour l’apprentissage :</p>
                <ul>
                  {learning.data.map((event) => (
                    <li key={event.learning_event_id}>{LEARNING_EVENT[event.event_type] ?? event.event_type}</li>
                  ))}
                </ul>
              </>
            )}
          </section>
        </aside>
      </div>
    </div>
  );
}
