"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { TypeDocument } from "@/components/documents/TypeDocument";
import { Icone } from "@/components/Icones";
import { JetonPraticien } from "@/components/JetonPraticien";
import { PiecesJointes } from "@/components/patients/PiecesJointes";
import { CorrectionPanel } from "@/components/review/CorrectionPanel";
import { DocumentBody } from "@/components/review/DocumentView";
import { Envois } from "@/components/review/Envois";
import { RailRevision } from "@/components/review/RailRevision";
import type { Selection } from "@/components/review/SourcePanel";
import { SpokenCorrectionPanel } from "@/components/review/SpokenCorrection";
import { TreatmentPlanCards } from "@/components/review/TreatmentPlanCards";
import styles from "@/components/review/consultation.module.css";
import { Barre, Bouton, Carte, Pastille, Zone } from "@/components/ui";
import {
  ApiError,
  apiRequest,
  type AudioSessionView,
  type ClinicalObjectView,
  type DocumentView,
  type Encounter,
  type Envoi,
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
import { useConcepts } from "@/lib/useConcepts";

/** Pendant l'écoute ou le traitement, le serveur refuse la suppression : on ne la propose pas. */
const EN_COURS = new Set(["recording", "paused", "finalizing", "processing"]);
const TERMINEES = new Set(["validated", "exported", "archived"]);

function tonConsultation(
  statut: string,
): "neutre" | "attention" | "valide" | "alerte" {
  if (statut === "review") return "attention";
  if (TERMINEES.has(statut)) return "valide";
  if (
    statut.endsWith("failed") ||
    statut.endsWith("error") ||
    statut === "upload_interrupted"
  )
    return "alerte";
  return "neutre";
}

function estValide(document: DocumentView): boolean {
  return document.status === "validated" || document.status === "exported";
}

function quand(iso: string): string {
  const date = new Date(iso);
  const jour = date.toLocaleDateString("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  const heure = date.toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  });
  return `${jour} à ${heure}`;
}

/** Une consultation, un document à la fois.
 *
 * Quand Oris a écrit plusieurs documents, chacun a son intercalaire : on sait toujours
 * sur lequel on travaille, et ce qu'on fait (réécrire, valider, noter un envoi) ne
 * touche que lui. Le dossier clinique, lui, est commun : il est à droite.
 */
export default function ConsultationPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
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
  const [envois, reloadEnvois] = useApi<Envoi[]>(
    `/encounters/${id}/deliveries`,
  );

  const [activeId, setActiveId] = useState<string | null>(null);
  const [selection, setSelection] = useState<Selection>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [feedback, setFeedback] = useState<{
    tone: "ok" | "error";
    text: string;
  } | null>(null);
  // Si le navigateur refuse le presse-papiers, le texte doit rester récupérable.
  const [copyFallback, setCopyFallback] = useState<string | null>(null);
  // Une réécriture appartient à un document : changer d'intercalaire ne la perd pas, et
  // elle ne s'affiche jamais sous un autre.
  const [edition, setEdition] = useState<{
    documentId: string;
    texte: string;
  } | null>(null);
  const [suppression, setSuppression] = useState<
    "fermee" | "confirmer" | "en_cours"
  >("fermee");
  const motDe = useConcepts();

  function erreur(caught: unknown) {
    const code = caught instanceof ApiError ? caught.code : "UNKNOWN";
    setFeedback({ tone: "error", text: errorMessage(code) });
  }

  function reloadAll() {
    reloadEncounter();
    reloadDocuments();
    reloadClinical();
    reloadLearning();
    reloadEnvois();
    setSelection(null);
  }

  function choisir(document: DocumentView) {
    setActiveId(document.id);
    setSelection(null);
    setFeedback(null);
    setCopyFallback(null);
    setAcknowledged(false);
  }

  async function enregistrerTexte(document: DocumentView) {
    if (edition === null) return;
    setFeedback(null);
    try {
      await apiRequest(`/documents/${document.id}/text`, {
        method: "POST",
        body: { content: edition.texte },
      });
      setEdition(null);
      setFeedback({
        tone: "ok",
        text: "Texte enregistré. Le dossier clinique est inchangé.",
      });
      reloadAll();
    } catch (caught) {
      erreur(caught);
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
      await apiRequest(`/encounters/${id}/documents/generate`, {
        method: "POST",
      });
      setFeedback({
        tone: "ok",
        text: "Comptes rendus plus courts, à partir de maintenant. Réversible dans « Oris apprend ».",
      });
      reloadAll();
    } catch (caught) {
      erreur(caught);
    }
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
    } catch (caught) {
      erreur(caught);
    }
  }

  async function copyForRecord(document: DocumentView) {
    setFeedback(null);
    setCopyFallback(null);
    let text: string;
    try {
      const { blob } = await fetchDocumentExport(document.id, "structured");
      text = await blob.text();
    } catch (caught) {
      erreur(caught);
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
    } catch (caught) {
      erreur(caught);
    }
  }

  async function supprimer() {
    setSuppression("en_cours");
    try {
      await apiRequest(`/encounters/${id}`, { method: "DELETE" });
      router.push("/consultations");
    } catch (caught) {
      setSuppression("confirmer");
      erreur(caught);
    }
  }

  if (encounter.state === "error") {
    return <p className="muted">{errorMessage(encounter.code)}</p>;
  }
  if (encounter.state !== "ready") {
    return <p className="muted">Chargement…</p>;
  }
  const data = encounter.data;
  const docs = (documents.state === "ready" ? documents.data : []).filter(
    (doc) => doc.status !== "superseded",
  );
  const active = docs.find((doc) => doc.id === activeId) ?? docs[0];
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
    ) && !docs.some((doc) => doc.document_type === "operative_note");
  const allValidated = docs.length > 0 && docs.every(estValide);
  const envoisDe = (documentId: string) =>
    envois.state === "ready"
      ? envois.data.filter((e) => e.document_id === documentId)
      : [];
  const enEdition =
    active && edition?.documentId === active.id ? edition : null;

  return (
    <div className="page" data-pleine-largeur>
      <header className={styles.entete}>
        <Link href="/consultations" className={styles.retour}>
          <Icone nom="retour" taille={15} /> Consultations
        </Link>
        <div className={styles.enteteLigne}>
          <div className={styles.identite}>
            <h1 className={styles.patient}>
              <Link href={`/patients/${data.patient.id}`}>
                {data.patient.last_name.toLocaleUpperCase("fr-FR")}{" "}
                <span className={styles.prenom}>{data.patient.first_name}</span>
              </Link>
            </h1>
            <p className={styles.quand}>
              <JetonPraticien
                nom={data.practitioner.name}
                titre={data.practitioner.title}
                taille="petit"
              />
              Consultation du {quand(data.started_at ?? data.created_at)}
              {data.synthetic_case_id &&
                ` · cas fictif ${data.synthetic_case_id}`}
            </p>
          </div>
          <div className={styles.actionsConsultation}>
            <Pastille ton={tonConsultation(data.status)}>
              {ENCOUNTER_STATUS[data.status]}
            </Pastille>
            {shadow && <Pastille ton="attention">mode ombre</Pastille>}
            {!shadow && data.status === "review" && (
              <Bouton
                disabled={!allValidated}
                title={
                  allValidated
                    ? undefined
                    : "Validez d’abord chaque document, un par un."
                }
                onClick={() =>
                  act(
                    `/encounters/${id}/validate`,
                    undefined,
                    "Consultation validée.",
                  )
                }
              >
                Valider la consultation
              </Bouton>
            )}
            {!EN_COURS.has(data.status) && (
              <button
                type="button"
                className={styles.supprimer}
                onClick={() => setSuppression("confirmer")}
                title="Supprimer cette consultation"
              >
                <Icone nom="corbeille" taille={16} />
                Supprimer
              </button>
            )}
          </div>
        </div>
      </header>

      {suppression !== "fermee" && (
        <div
          className={`banner banner-critical ${styles.confirmation}`}
          role="alertdialog"
        >
          <div>
            <strong>Supprimer cette consultation ?</strong> Le son s’il en
            reste, la transcription, le dossier clinique
            {docs.length > 0 &&
              ` et ${docs.length > 1 ? `les ${docs.length} documents` : "le document"}`}{" "}
            seront effacés, sans retour possible. Le patient et ses pièces
            jointes restent.
            {docs.some(estValide) &&
              " Un document validé a peut-être déjà été versé au dossier : il y restera."}
          </div>
          <Barre>
            <button
              type="button"
              className={styles.supprimerFort}
              disabled={suppression === "en_cours"}
              onClick={() => void supprimer()}
            >
              {suppression === "en_cours"
                ? "Suppression…"
                : "Supprimer définitivement"}
            </button>
            <Bouton
              variante="secondaire"
              onClick={() => setSuppression("fermee")}
            >
              Annuler
            </Bouton>
          </Barre>
        </div>
      )}

      {data.processing_errors.some((e) => PROCESSING_RULE[e.rule]) && (
        <div className="banner banner-review" role="alert">
          {data.processing_errors
            .map((e) => PROCESSING_RULE[e.rule])
            .filter(Boolean)
            .join(" ")}
          {data.processing_errors.some((e) => e.rule === "STT_UNAVAILABLE") && (
            <div>
              <Bouton
                variante="secondaire"
                onClick={() =>
                  act(
                    `/encounters/${id}/process`,
                    undefined,
                    "Traitement relancé.",
                  )
                }
              >
                Relancer le traitement
              </Bouton>
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
      {reviewWarnings.map((warning) => (
        <div key={warning.code} className="banner banner-review" role="status">
          <strong>À vérifier</strong> — {warning.message}
        </div>
      ))}

      <div className={styles.disposition}>
        <section className={styles.classeur} aria-label="Documents">
          {docs.length === 0 && (
            <Carte>
              <p className="muted" style={{ margin: 0 }}>
                Aucun document pour cette consultation.
              </p>
            </Carte>
          )}

          {docs.length > 0 && active && (
            <>
              <div
                className={styles.intercalaires}
                role="tablist"
                aria-label="Documents rédigés"
              >
                {docs.map((doc) => {
                  const partis = envoisDe(doc.id);
                  return (
                    <button
                      key={doc.id}
                      type="button"
                      role="tab"
                      aria-selected={doc.id === active.id}
                      data-type={doc.document_type}
                      className={styles.intercalaire}
                      onClick={() => choisir(doc)}
                    >
                      <TypeDocument type={doc.document_type} />
                      <span className={styles.intercalaireEtat}>
                        {estValide(doc) ? (
                          <span className={styles.etatValide}>
                            <Icone nom="valide" taille={12} /> Validé
                          </span>
                        ) : (
                          <span className={styles.etatARelire}>
                            {DOCUMENT_STATUS[doc.status]}
                          </span>
                        )}
                        {partis.length > 0 && (
                          <span className={styles.etatEnvoye}>
                            <Icone nom="envoi" taille={12} /> envoyé
                          </span>
                        )}
                        {edition?.documentId === doc.id && (
                          <span className={styles.etatEdition}>
                            réécriture en cours
                          </span>
                        )}
                      </span>
                    </button>
                  );
                })}
                {operativeProposed && !shadow && (
                  <button
                    type="button"
                    className={styles.intercalaireAjout}
                    title="Un acte a été détecté. Rédigé seulement à partir de ce qui a été dit pendant l’intervention."
                    onClick={() =>
                      act(
                        `/encounters/${id}/documents/operative-note`,
                        undefined,
                        "Compte rendu de soins rédigé.",
                      )
                    }
                  >
                    + Compte rendu de soins
                    <span className={styles.intercalaireEtat}>
                      un acte a été détecté
                    </span>
                  </button>
                )}
              </div>

              <article
                className={styles.feuille}
                data-type={active.document_type}
                role="tabpanel"
                aria-label={DOCUMENT_TYPE[active.document_type]}
              >
                <header className={styles.feuilleEntete}>
                  <div>
                    <h2 className={styles.feuilleTitre}>
                      {DOCUMENT_TYPE[active.document_type]}
                    </h2>
                    <p className={styles.feuilleVersion}>
                      {DOCUMENT_STATUS[active.status]} · version{" "}
                      {active.version} · rédigé depuis le dossier clinique v
                      {active.generated_from_object_version}
                    </p>
                  </div>
                  {!shadow && !enEdition && (
                    <div className={styles.outils}>
                      <Bouton
                        variante="discret"
                        onClick={() =>
                          setEdition({
                            documentId: active.id,
                            texte: active.content,
                          })
                        }
                      >
                        Éditer
                      </Bouton>
                      <Bouton
                        variante="discret"
                        onClick={() => void raccourcir()}
                      >
                        Raccourcir
                      </Bouton>
                      <Bouton
                        variante="discret"
                        onClick={() => void copyForRecord(active)}
                      >
                        Copier
                      </Bouton>
                      <Bouton
                        variante="secondaire"
                        onClick={() => void exportDocument(active)}
                      >
                        PDF
                      </Bouton>
                    </div>
                  )}
                </header>

                {feedback && (
                  <div
                    className={`banner ${feedback.tone === "ok" ? "banner-info" : "banner-critical"}`}
                    role="status"
                  >
                    {feedback.text}
                  </div>
                )}

                {!active.is_current && (
                  <div className="banner banner-review">
                    Ce document a été rédigé avant la dernière correction du
                    dossier clinique.
                    <div>
                      <Bouton
                        variante="secondaire"
                        onClick={() =>
                          act(
                            `/encounters/${id}/documents/generate`,
                            undefined,
                            "Documents régénérés.",
                          )
                        }
                      >
                        Régénérer les documents
                      </Bouton>
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

                {enEdition === null ? (
                  <div className={styles.texte}>
                    <DocumentBody
                      document={active}
                      selected={
                        selection?.kind === "claim" ? selection.claim : null
                      }
                      onSelect={(claim) =>
                        setSelection({ kind: "claim", claim })
                      }
                    />
                  </div>
                ) : (
                  <div style={{ display: "grid", gap: 12 }}>
                    <div className="banner banner-review">
                      Vous réécrivez le texte de ce document seulement. Le
                      dossier clinique ne changera pas : si une donnée clinique
                      est fausse, corrigez-la plutôt à droite.
                    </div>
                    <Zone
                      value={enEdition.texte}
                      autoFocus
                      aria-label="Texte du document"
                      onChange={(event) =>
                        setEdition({
                          documentId: active.id,
                          texte: event.target.value,
                        })
                      }
                    />
                    <Barre>
                      <Bouton onClick={() => void enregistrerTexte(active)}>
                        Enregistrer
                      </Bouton>
                      <Bouton
                        variante="secondaire"
                        onClick={() => setEdition(null)}
                      >
                        Annuler
                      </Bouton>
                    </Barre>
                  </div>
                )}

                {active.generator.startsWith("practitioner") &&
                  enEdition === null && (
                    <p className="muted" style={{ margin: 0 }}>
                      Texte réécrit à la main : la provenance phrase par phrase
                      n’est plus disponible sur ce document.
                    </p>
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
                      style={{
                        width: "100%",
                        fontFamily: "inherit",
                        padding: 8,
                      }}
                    />
                  </label>
                )}

                {!shadow && (
                  <footer className={styles.feuillePied}>
                    <Envois
                      documentId={active.id}
                      patientId={data.patient.id}
                      envois={envoisDe(active.id)}
                      onChange={reloadAll}
                    />

                    {!estValide(active) && (
                      <div className={styles.validation}>
                        {criticalWarnings.length > 0 && (
                          <label className={styles.prisConnaissance}>
                            <input
                              type="checkbox"
                              checked={acknowledged}
                              onChange={(event) =>
                                setAcknowledged(event.target.checked)
                              }
                            />
                            J’ai pris connaissance de l’alerte critique : ce
                            document n’est pas exhaustif.
                          </label>
                        )}
                        <Bouton
                          disabled={
                            !active.is_current ||
                            enEdition !== null ||
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
                          Valider :{" "}
                          {DOCUMENT_TYPE[
                            active.document_type
                          ].toLocaleLowerCase("fr-FR")}
                        </Bouton>
                        <span className={styles.noteValidation}>
                          Non validé, le PDF porte la mention « brouillon ».
                        </span>
                      </div>
                    )}
                  </footer>
                )}
              </article>
            </>
          )}
        </section>

        <aside className={styles.rail}>
          {/* Sans dossier clinique (transcription échouée), les repères posés
              pendant l'écoute restent visibles : le geste n'est pas perdu. */}
          {!object && marks.state === "ready" && marks.data.length > 0 && (
            <Carte titre="Points marqués">
              <p className="muted" style={{ marginTop: 0 }}>
                Les moments que vous avez marqués pendant la consultation.
              </p>
              <ul className="liste-simple">
                {marks.data.map((mark) => (
                  <li key={mark.timestamp_ms}>
                    à {formatDuration(mark.timestamp_ms)}
                  </li>
                ))}
              </ul>
            </Carte>
          )}
          {object && active && (
            <RailRevision
              document={active}
              clinicalObject={object}
              versions={
                clinical.state === "ready" ? clinical.data.versions : []
              }
              transcript={transcript.state === "ready" ? transcript.data : null}
              learning={learning.state === "ready" ? learning.data : []}
              marks={marks.state === "ready" ? marks.data : []}
              selection={selection}
              onSelect={setSelection}
              motDe={motDe}
            />
          )}

          {/* Replié par défaut : on corrige quand on a vu une erreur, pas à chaque fois. */}
          {object && !shadow && (
            <details className={styles.replie}>
              <summary>Corriger le dossier clinique</summary>
              <div className={styles.replieContenu} style={{ display: "grid", gap: 12 }}>
                <p className="muted" style={{ margin: 0 }}>
                  Une correction modifie d’abord le dossier clinique ; Oris réécrit ensuite tous
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
              </div>
            </details>
          )}

          {/* Les pièces du patient : utiles pour s'y référer, pas à chaque consultation.
              Repliées, elles ne prennent qu'une ligne. Une pièce déposée ici est
              rattachée à cette consultation. */}
          <details className={styles.replie}>
            <summary>
              Pièces jointes
              <Link href={`/patients/${data.patient.id}`} className="link-button">
                fiche patient
              </Link>
            </summary>
            <div className={styles.replieContenu}>
              <PiecesJointes patientId={data.patient.id} encounterId={data.id} compact />
            </div>
          </details>

          {audio.state === "ready" && (
            <p className={styles.audio}>
              Audio : {formatDuration(audio.data.received_duration_ms)} reçues
              en {audio.data.received_count} segment(s)
              {audio.data.gaps.length === 0 ? ", sans interruption" : ""}.{" "}
              {audio.data.purge_status === "purged"
                ? `Son supprimé après traitement (${formatDateTime(audio.data.purged_at)}).`
                : "Son conservé jusqu’à la fin du traitement."}
            </p>
          )}
        </aside>
      </div>
    </div>
  );
}
