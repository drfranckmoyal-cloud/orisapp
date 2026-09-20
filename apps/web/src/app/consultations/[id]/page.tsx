"use client";

import { useParams } from "next/navigation";
import { useState } from "react";

import { CorrectionPanel } from "@/components/review/CorrectionPanel";
import { SpokenCorrectionPanel } from "@/components/review/SpokenCorrection";
import { TreatmentPlanCards } from "@/components/review/TreatmentPlanCards";
import { DocumentBody } from "@/components/review/DocumentView";
import styles from "@/components/review/review.module.css";
import { RailRevision } from "@/components/review/RailRevision";
import type { Selection } from "@/components/review/SourcePanel";
import { Barre, Bouton, Carte, Zone } from "@/components/ui";
import { useConcepts } from "@/lib/useConcepts";
import {
  ApiError,
  apiRequest,
  type AudioSessionView,
  type ClinicalObjectView,
  type DocumentView,
  type Encounter,
  fetchDocumentExport,
  type LearningEventView,
  type Mark,
  type TranscriptView,
} from "@/lib/api";
import {
  DOCUMENT_STATUS,
  DOCUMENT_TYPE,
  ENCOUNTER_STATUS,
  PROCESSING_RULE,
  errorMessage,
  formatDateTime,
  formatDuration,
} from "@/lib/labels";
import { useApi } from "@/lib/useApi";

function statusChipClass(status: DocumentView["status"]): string {
  if (status === "validated") return "chip chip-success";
  if (status === "outdated" || status === "needs_review")
    return "chip chip-review";
  return "chip";
}

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const [encounter, reloadEncounter] = useApi<Encounter>(`/encounters/${id}`);
  const [documents, reloadDocuments] = useApi<DocumentView[]>(
    `/encounters/${id}/documents`,
  );
  const [clinical, reloadClinical] = useApi<ClinicalObjectView>(
    `/encounters/${id}/clinical-object`,
  );
  const [transcript] = useApi<TranscriptView>(`/encounters/${id}/transcript`);
  const [learning, reloadLearning] = useApi<LearningEventView[]>(
    `/encounters/${id}/learning-events`,
  );
  const [audio] = useApi<AudioSessionView>(`/encounters/${id}/audio`);
  const [marks] = useApi<Mark[]>(`/encounters/${id}/marks`);

  const [activeType, setActiveType] =
    useState<DocumentView["document_type"]>("consultation_note");
  const [selection, setSelection] = useState<Selection>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [feedback, setFeedback] = useState<{
    tone: "ok" | "error";
    text: string;
  } | null>(null);
  // Si le navigateur refuse le presse-papiers, le texte doit rester récupérable.
  const [copyFallback, setCopyFallback] = useState<string | null>(null);
  const motDe = useConcepts();
  const [edition, setEdition] = useState<string | null>(null);

  async function enregistrerTexte(document: DocumentView) {
    if (edition === null) return;
    setFeedback(null);
    try {
      await apiRequest(`/documents/${document.id}/text`, {
        method: "POST",
        body: { content: edition },
      });
      setEdition(null);
      setFeedback({ tone: "ok", text: "Texte enregistré. Le dossier clinique est inchangé." });
      reloadAll();
    } catch (error) {
      const code = error instanceof ApiError ? error.code : "UNKNOWN";
      setFeedback({ tone: "error", text: errorMessage(code) });
    }
  }

  /** Raccourcir = une préférence de rédaction, appliquée à partir de maintenant (§53). */
  async function raccourcir() {
    setFeedback(null);
    try {
      await apiRequest("/me/preferences", {
        method: "PATCH",
        body: { document_length: "concise" },
      });
      await apiRequest(`/encounters/${id}/documents/generate`, { method: "POST" });
      setFeedback({
        tone: "ok",
        text: "Comptes rendus plus courts, à partir de maintenant. Réversible dans « Oris apprend ».",
      });
      reloadAll();
    } catch (error) {
      const code = error instanceof ApiError ? error.code : "UNKNOWN";
      setFeedback({ tone: "error", text: errorMessage(code) });
    }
  }

  function reloadAll() {
    reloadEncounter();
    reloadDocuments();
    reloadClinical();
    reloadLearning();
    setSelection(null);
  }

  async function exportDocument(document: DocumentView) {
    setFeedback(null);
    try {
      const { blob, filename } = await fetchDocumentExport(document.id, "pdf");
      const url = URL.createObjectURL(blob);
      const link = window.document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
      setFeedback({ tone: "ok", text: `PDF téléchargé (${filename}).` });
      reloadAll();
    } catch (error) {
      const code = error instanceof ApiError ? error.code : "UNKNOWN";
      setFeedback({ tone: "error", text: errorMessage(code) });
    }
  }

  async function copyForRecord(document: DocumentView) {
    setFeedback(null);
    setCopyFallback(null);
    let text: string;
    try {
      const { blob } = await fetchDocumentExport(document.id, "structured");
      text = await blob.text();
    } catch (error) {
      const code = error instanceof ApiError ? error.code : "UNKNOWN";
      setFeedback({ tone: "error", text: errorMessage(code) });
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      setFeedback({
        tone: "ok",
        text: "Copié : collez-le dans le dossier du patient.",
      });
    } catch {
      // Presse-papiers refusé (navigateur, permission) : on montre le texte.
      setCopyFallback(text);
      setFeedback({ tone: "error", text: errorMessage("COPY_FAILED") });
    }
    reloadAll();
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
  const active =
    docs.find((doc) => doc.document_type === activeType) ?? docs[0];
  const object =
    clinical.state === "ready" ? clinical.data.clinical_object : null;
  const criticalWarnings =
    object?.warnings.filter((warning) => warning.severity === "critical") ?? [];
  // Alertes non bloquantes : à voir avant de signer, sans interdire la validation.
  const reviewWarnings =
    object?.warnings.filter((warning) => warning.severity === "review") ?? [];
  // M11 : en mode ombre, Oris écrit pour être mesuré, pas pour être utilisé.
  const shadow = data.mode === "shadow";
  // §81 : un acte a été dit, mais le compte rendu de soins ne se crée jamais tout seul.
  const operativeProposed =
    (object?.procedures ?? []).some(
      (procedure) => procedure.status !== "cancelled",
    ) &&
    !docs.some(
      (doc) =>
        doc.document_type === "operative_note" && doc.status !== "superseded",
    );
  const allValidated =
    docs.length > 0 &&
    docs
      .filter((d) => d.status !== "superseded")
      .every((d) => d.status === "validated");

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="subtitle">
            Consultation du {formatDateTime(data.started_at ?? data.created_at)}
            {data.synthetic_case_id &&
              ` · cas fictif ${data.synthetic_case_id}`}
          </p>
          <h1>
            {data.patient.first_name} {data.patient.last_name}
          </h1>
        </div>
        <div
          style={{
            display: "flex",
            gap: 8,
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <span className="chip">{ENCOUNTER_STATUS[data.status]}</span>
          {data.mode === "shadow" && (
            <span className="chip chip-review">mode ombre</span>
          )}
          {object && (
            <span className="chip">
              Dossier clinique v{object.object_version}
            </span>
          )}
          <button
            type="button"
            className="button button-primary"
            hidden={data.mode === "shadow"}
            disabled={!allValidated || data.status !== "review"}
            onClick={() =>
              act(
                `/encounters/${id}/validate`,
                undefined,
                "Consultation validée.",
              )
            }
          >
            Valider la consultation
          </button>
        </div>
      </header>

      {data.processing_errors.some((e) => PROCESSING_RULE[e.rule]) && (
        <div className="banner banner-review" role="alert">
          {data.processing_errors
            .map((e) => PROCESSING_RULE[e.rule])
            .filter(Boolean)
            .join(" ")}
          {data.processing_errors.some((e) => e.rule === "STT_UNAVAILABLE") && (
            <div>
              <button
                type="button"
                className="button button-secondary"
                onClick={() =>
                  act(
                    `/encounters/${id}/process`,
                    undefined,
                    "Traitement relancé.",
                  )
                }
              >
                Relancer le traitement
              </button>
            </div>
          )}
        </div>
      )}
      {data.processing_errors.some((e) => !PROCESSING_RULE[e.rule]) && (
        <div className="banner banner-critical" role="alert">
          Oris a refusé le résultat de l’extraction plutôt que de le corriger en
          silence :{" "}
          {data.processing_errors
            .filter((e) => !PROCESSING_RULE[e.rule])
            .map((e) => `${e.rule} (${e.subject_id})`)
            .join(", ")}
          .
        </div>
      )}
      {audio.state === "ready" && audio.data.gaps.length > 0 && (
        <div className="banner banner-critical" role="alert">
          <strong>Audio incomplet</strong> — {audio.data.gaps.length}{" "}
          interruption(s) de captation. Une partie de la consultation n’a pas
          été enregistrée.
        </div>
      )}
      {audio.state === "ready" && (
        <section className="card" aria-labelledby="audio-heading">
          <h2 id="audio-heading">Audio</h2>
          <p style={{ margin: 0 }}>
            {formatDuration(audio.data.received_duration_ms)} reçues en{" "}
            {audio.data.received_count} segment(s)
            {audio.data.gaps.length === 0 ? ", sans interruption." : "."}
          </p>
          <p className="muted">
            {audio.data.purge_status === "purged"
              ? `Son supprimé après traitement (${formatDateTime(audio.data.purged_at)}). Seules les informations techniques de réception sont conservées.`
              : "Son conservé temporairement jusqu’à la fin du traitement."}
          </p>
        </section>
      )}
      {criticalWarnings.map((warning) => (
        <div key={warning.code} className="banner banner-critical" role="alert">
          <strong>Alerte critique</strong> — {warning.message} Le compte rendu
          ne peut pas être considéré comme exhaustif.
        </div>
      ))}
      {shadow && (
        <div className="banner banner-review" role="status">
          <strong>Mode ombre</strong> — Oris travaille en parallèle pour être
          comparé à votre propre compte rendu. Rien de ce qu’il écrit ici ne
          peut être validé, exporté ni versé au dossier.
        </div>
      )}

      {operativeProposed && (
        <div className="banner banner-info" role="status">
          <strong>Un acte a été détecté</strong> — voulez-vous le compte rendu
          de soins ? Il ne sera rédigé qu’à partir de ce qui a été dit pendant
          l’intervention.
          <div>
            <button
              type="button"
              className="button button-primary"
              onClick={() =>
                act(
                  `/encounters/${id}/documents/operative-note`,
                  undefined,
                  "Compte rendu de soins rédigé.",
                )
              }
            >
              Générer le compte rendu de soins
            </button>
          </div>
        </div>
      )}

      {reviewWarnings.map((warning) => (
        <div key={warning.code} className="banner banner-review" role="status">
          <strong>À vérifier</strong> — {warning.message}
        </div>
      ))}
      {feedback && (
        <div
          className={`banner ${feedback.tone === "ok" ? "banner-info" : "banner-critical"}`}
          role="status"
        >
          {feedback.text}
        </div>
      )}

      <div className={styles.layout}>
        <section className="card" aria-label="Documents">
          {docs.length === 0 && (
            <p className="muted">Aucun document pour cette consultation.</p>
          )}
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
              <div
                style={{
                  display: "flex",
                  gap: 8,
                  flexWrap: "wrap",
                  alignItems: "center",
                }}
              >
                <span className={statusChipClass(active.status)}>
                  {DOCUMENT_STATUS[active.status]}
                </span>
                <span className="muted">
                  Version {active.version} · rédigé depuis le dossier clinique v
                  {active.generated_from_object_version}
                </span>
              </div>

              {!active.is_current && (
                <div className="banner banner-review">
                  Ce document a été rédigé avant la dernière correction du
                  dossier clinique.
                  <div>
                    <button
                      type="button"
                      className="button button-secondary"
                      onClick={() =>
                        act(
                          `/encounters/${id}/documents/generate`,
                          undefined,
                          "Documents régénérés.",
                        )
                      }
                    >
                      Régénérer les documents
                    </button>
                  </div>
                </div>
              )}

              {active.document_type === "treatment_plan_text" && object && (
                <TreatmentPlanCards
                  encounter={data}
                  clinicalObject={object}
                  onSelectFact={(factId) =>
                    setSelection({ kind: "fact", factId })
                  }
                  onCorrected={reloadAll}
                />
              )}

              {edition === null ? (
                <DocumentBody
                  document={active}
                  selected={selection?.kind === "claim" ? selection.claim : null}
                  onSelect={(claim) => setSelection({ kind: "claim", claim })}
                />
              ) : (
                <div style={{ display: "grid", gap: 12 }}>
                  <div className="banner banner-review">
                    Vous réécrivez le texte. Le dossier clinique ne changera pas : si une
                    donnée clinique est fausse, corrigez-la plutôt à droite.
                  </div>
                  <Zone
                    value={edition}
                    autoFocus
                    aria-label="Texte du document"
                    onChange={(event) => setEdition(event.target.value)}
                  />
                  <Barre>
                    <Bouton onClick={() => void enregistrerTexte(active)}>Enregistrer</Bouton>
                    <Bouton variante="secondaire" onClick={() => setEdition(null)}>
                      Annuler
                    </Bouton>
                  </Barre>
                </div>
              )}

              {active.generator.startsWith("practitioner") && edition === null && (
                <p className="muted" style={{ margin: 0 }}>
                  Texte réécrit à la main : la provenance phrase par phrase n’est plus
                  disponible sur ce document.
                </p>
              )}

              {!shadow && edition === null && (
                <div className="barre-document">
                  <Bouton variante="secondaire" onClick={() => setEdition(active.content)}>
                    Éditer le texte
                  </Bouton>
                  <Bouton variante="secondaire" onClick={() => void raccourcir()}>
                    Raccourcir
                  </Bouton>
                  <Bouton variante="secondaire" onClick={() => copyForRecord(active)}>
                    Copier pour le dossier
                  </Bouton>
                  <Bouton variante="secondaire" onClick={() => exportDocument(active)}>
                    Exporter en PDF
                  </Bouton>
                  {active.status !== "validated" && active.status !== "exported" && (
                    <span className="muted">
                      Non validé : le PDF portera la mention « brouillon ».
                    </span>
                  )}
                </div>
              )}

              {copyFallback !== null && (
                <label style={{ display: "grid", gap: 8 }}>
                  Sélectionnez ce texte et copiez-le (Cmd+C) :
                  <textarea
                    readOnly
                    rows={8}
                    value={copyFallback}
                    onFocus={(event) => event.currentTarget.select()}
                    autoFocus
                    style={{ width: "100%", fontFamily: "inherit", padding: 8 }}
                  />
                </label>
              )}

              {!shadow &&
                active.status !== "validated" &&
                active.status !== "exported" &&
                active.status !== "superseded" && (
                  <div
                    style={{
                      display: "grid",
                      gap: 12,
                      borderTop: "1px solid var(--color-cloud)",
                      paddingTop: 16,
                    }}
                  >
                    {criticalWarnings.length > 0 && (
                      <label
                        style={{
                          display: "flex",
                          gap: 8,
                          alignItems: "flex-start",
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={acknowledged}
                          onChange={(event) =>
                            setAcknowledged(event.target.checked)
                          }
                          style={{ width: 20, height: 20 }}
                        />
                        J’ai pris connaissance de l’alerte critique : ce
                        document n’est pas exhaustif.
                      </label>
                    )}
                    <div>
                      <button
                        type="button"
                        className="button button-primary"
                        disabled={
                          !active.is_current ||
                          (criticalWarnings.length > 0 && !acknowledged)
                        }
                        onClick={() =>
                          act(
                            `/documents/${active.id}/validate`,
                            {
                              acknowledged_warning_codes: acknowledged
                                ? criticalWarnings.map((w) => w.code)
                                : [],
                            },
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
          {/* Sans dossier clinique (transcription échouée), les repères posés
              pendant l'écoute restent visibles : le geste n'est pas perdu. */}
          {!object && marks.state === "ready" && marks.data.length > 0 && (
            <Carte titre="Points marqués">
              <p className="muted" style={{ marginTop: 0 }}>
                Les moments que vous avez marqués pendant la consultation.
              </p>
              <ul className="liste-simple">
                {marks.data.map((mark) => (
                  <li key={mark.timestamp_ms}>à {formatDuration(mark.timestamp_ms)}</li>
                ))}
              </ul>
            </Carte>
          )}
          {object && (
            <RailRevision
              document={active}
              clinicalObject={object}
              versions={clinical.state === "ready" ? clinical.data.versions : []}
              transcript={transcript.state === "ready" ? transcript.data : null}
              learning={learning.state === "ready" ? learning.data : []}
              marks={marks.state === "ready" ? marks.data : []}
              selection={selection}
              onSelect={setSelection}
              motDe={motDe}
            />
          )}

          {object && !shadow && (
            <Carte titre="Corriger">
              <p className="muted" style={{ margin: 0 }}>
                Une correction modifie d’abord le dossier clinique ; Oris réécrit ensuite
                les documents.
              </p>
              <SpokenCorrectionPanel
                encounter={data}
                clinicalObject={object}
                onCorrected={reloadAll}
              />
              <details>
                <summary>Corriger sans dicter</summary>
                <div style={{ marginTop: 12 }}>
                  <CorrectionPanel
                    encounter={data}
                    clinicalObject={object}
                    onCorrected={reloadAll}
                  />
                </div>
              </details>
            </Carte>
          )}
        </aside>
      </div>
    </div>
  );
}
