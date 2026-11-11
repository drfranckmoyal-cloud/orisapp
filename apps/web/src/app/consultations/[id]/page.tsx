"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { TypeDocument } from "@/components/documents/TypeDocument";
import { Icone } from "@/components/Icones";
import { JetonPraticien } from "@/components/JetonPraticien";
import { PiecesJointes } from "@/components/patients/PiecesJointes";
import { SmileCloud } from "@/components/patients/SmileCloud";
import {
  AssistantCorrection,
  type AssistantHandle,
} from "@/components/review/AssistantCorrection";
import { CorrectionPanel } from "@/components/review/CorrectionPanel";
import { CorrespondantRapide } from "@/components/review/CorrespondantRapide";
import { Documentation } from "@/components/review/Documentation";
import { EnvoiDocument } from "@/components/review/EnvoiDocument";
import { Envois } from "@/components/review/Envois";
import { PlanVisuel } from "@/components/review/PlanVisuel";
import { RailRevision } from "@/components/review/RailRevision";
import type { Selection } from "@/components/review/SourcePanel";
import {
  type EtatTexte,
  TexteModifiable,
} from "@/components/review/TexteModifiable";
import { TreatmentPlanCards } from "@/components/review/TreatmentPlanCards";
import styles from "@/components/review/consultation.module.css";
import mise from "@/components/review/relecture.module.css";
import { Barre, Bouton, Carte, Pastille } from "@/components/ui";
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
  messageRegle,
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

/** Les documents que Claude rédige en paragraphes : les seuls qu'il sait relire. */
const REDIGES = new Set(["consultation_note", "referral_letter"]);

/** Une consultation, un document à la fois.
 *
 * Réorganisée le 10/11/2026 (Franck : « je m'y perds vraiment »). Trois zones, dans
 * l'ordre où l'on s'en sert : un en-tête qui reste en haut (qui, où on en est, l'action
 * du moment), le document comme une feuille qu'on modifie en cliquant dedans, et à droite
 * le dialogue de correction puis ce qu'il faut vérifier. Aucune fonction n'a disparu :
 * ce qu'on fait rarement est rangé dans les menus « ⋯ ».
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
  // Le texte s'édite à même la page et s'enregistre tout seul : on dit où il en est.
  const [etatTexte, setEtatTexte] = useState<{
    etat: EtatTexte;
    message?: string;
  }>({ etat: "repos" });
  const assistant = useRef<AssistantHandle | null>(null);
  // Un correspondant rattaché ici doit apparaître dans les destinataires de l'envoi.
  const [versionEnvoi, setVersionEnvoi] = useState(0);
  const [suppression, setSuppression] = useState<
    "fermee" | "confirmer" | "en_cours"
  >("fermee");
  // Les fichiers rapatriés de SmileCloud rechargent la liste des pièces jointes.
  const [versionPieces, setVersionPieces] = useState(0);
  const motDe = useConcepts();
  const [toast, setToast] = useState<string | null>(null);
  const [confirmerRetrait, setConfirmerRetrait] = useState<string | null>(null);

  // Le dossier se prépare en arrière-plan depuis le 10/11/2026 : la page le guette et
  // s'actualise seule, sans qu'on ait à recharger.
  const enPreparation =
    encounter.state === "ready" &&
    (encounter.data.status === "finalizing" ||
      encounter.data.status === "processing");
  useEffect(() => {
    if (!enPreparation) return;
    const veille = window.setInterval(() => {
      reloadEncounter();
      reloadDocuments();
      reloadClinical();
    }, 6000);
    return () => window.clearInterval(veille);
  }, [enPreparation, reloadEncounter, reloadDocuments, reloadClinical]);

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
    setEtatTexte({ etat: "repos" });
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

  /** Valide le document ouvert, et le dit dans une petite fenêtre qui s'efface. */
  async function valider(document: DocumentView) {
    setFeedback(null);
    try {
      await apiRequest(`/documents/${document.id}/validate`, {
        method: "POST",
        body: {
          acknowledged_warning_codes: acknowledged
            ? criticalWarnings.map((w) => w.code)
            : [],
        },
      });
      setToast(`${DOCUMENT_TYPE[document.document_type]} validé.`);
      window.setTimeout(() => setToast(null), 3500);
      reloadAll();
    } catch (caught) {
      erreur(caught);
    }
  }

  /** Retire un document demandé (courrier d'adressage, compte rendu opératoire). */
  async function retirerDocument(document: DocumentView) {
    setConfirmerRetrait(null);
    try {
      await apiRequest(`/documents/${document.id}`, { method: "DELETE" });
      setActiveId(null);
      setToast(`${DOCUMENT_TYPE[document.document_type]} supprimé.`);
      window.setTimeout(() => setToast(null), 3500);
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
  const envoisDe = (documentId: string) =>
    envois.state === "ready"
      ? envois.data.filter((e) => e.document_id === documentId)
      : [];
  const enSaisie =
    etatTexte.etat === "saisie" || etatTexte.etat === "enregistrement";
  const valide = active ? estValide(active) : false;
  const envoye = active ? envoisDe(active.id).length > 0 : false;
  const nomDocument = active
    ? DOCUMENT_TYPE[active.document_type].toLocaleLowerCase("fr-FR")
    : "document";
  const corrigeable =
    !shadow && ["review", "validated", "exported"].includes(data.status);

  return (
    <div className="page" data-pleine-largeur>
      {/* 1. L'en-tête reste en haut : le patient, l'étape, l'action du moment. */}
      <header className={mise.entete}>
        <Link href="/consultations" className={mise.retour}>
          <Icone nom="retour" taille={15} /> Consultations
        </Link>
        <div className={mise.ligne}>
          <div className={mise.identite}>
            <h1 className={mise.patient}>
              <Link href={`/patients/${data.patient.id}`}>
                {data.patient.last_name.toLocaleUpperCase("fr-FR")}{" "}
                <span className={mise.prenom}>{data.patient.first_name}</span>
              </Link>
            </h1>
            <p className={mise.quand}>
              <JetonPraticien
                nom={data.practitioner.name}
                titre={data.practitioner.title}
                taille="petit"
              />
              {quand(data.started_at ?? data.created_at)}
              {data.synthetic_case_id &&
                ` · cas fictif ${data.synthetic_case_id}`}
            </p>
          </div>
          <span className={mise.pousse} />
          {active && !shadow && (
            <ol className={mise.etapes} aria-label="Avancement">
              <li data-etat={valide ? "fait" : "encours"}>
                <i aria-hidden="true" />
                Relire
              </li>
              <li data-etat={valide ? "fait" : "attente"}>
                <i aria-hidden="true" />
                Valider
              </li>
              <li data-etat={envoye ? "fait" : valide ? "encours" : "attente"}>
                <i aria-hidden="true" />
                Envoyer
              </li>
            </ol>
          )}
          <div className={mise.actions}>
            {!active && (
              <Pastille ton={tonConsultation(data.status)}>
                {ENCOUNTER_STATUS[data.status]}
              </Pastille>
            )}
            {shadow && <Pastille ton="attention">mode ombre</Pastille>}
            {active && !shadow && !valide && (
              <Bouton
                disabled={
                  !active.is_current ||
                  enSaisie ||
                  (criticalWarnings.length > 0 && !acknowledged)
                }
                title={
                  criticalWarnings.length > 0 && !acknowledged
                    ? "Cochez d’abord la prise de connaissance de l’alerte, à droite"
                    : undefined
                }
                onClick={() => void valider(active)}
              >
                <Icone nom="valide" taille={16} /> Valider le {nomDocument}
              </Bouton>
            )}
            {active && !shadow && valide && (
              <>
                <span className={mise.valide}>
                  <Icone nom="valide" taille={15} /> Validé
                </span>
                <Bouton
                  variante={envoye ? "secondaire" : "principal"}
                  onClick={() =>
                    window.document
                      .getElementById("envoi")
                      ?.scrollIntoView({ behavior: "smooth", block: "start" })
                  }
                >
                  <Icone nom="envoi" taille={16} />{" "}
                  {envoye ? "Envoyer encore" : "Envoyer…"}
                </Bouton>
              </>
            )}
            <details className={mise.menu}>
              <summary
                title="Transcription, suppression"
                aria-label="Autres actions sur la consultation"
              >
                ⋯
              </summary>
              <div className={mise.menuContenu}>
                {/* Ce qui a été entendu, mot pour mot : le recours en cas de doute. */}
                <Link href={`/consultations/${id}/transcription`}>
                  Transcription de la consultation
                </Link>
                <Link href={`/patients/${data.patient.id}`}>Fiche du patient</Link>
                {!EN_COURS.has(data.status) && (
                  <button
                    type="button"
                    data-danger="true"
                    onClick={() => setSuppression("confirmer")}
                  >
                    <Icone nom="corbeille" taille={15} /> Supprimer la
                    consultation
                  </button>
                )}
              </div>
            </details>
          </div>
        </div>

        {/* 2. Un onglet par document, large, avec son état. */}
        {docs.length > 0 && active && (
          <div className={mise.onglets} role="tablist" aria-label="Documents rédigés">
            {docs.map((doc) => (
              <button
                key={doc.id}
                type="button"
                role="tab"
                aria-selected={doc.id === active.id}
                className={mise.onglet}
                onClick={() => choisir(doc)}
              >
                {DOCUMENT_TYPE[doc.document_type]}
                {estValide(doc) ? (
                  <span className={mise.etat} data-etat="valide">
                    <Icone nom="valide" taille={12} /> Validé
                  </span>
                ) : (
                  <span className={mise.etat}>{DOCUMENT_STATUS[doc.status]}</span>
                )}
                {envoisDe(doc.id).length > 0 && (
                  <span className={mise.etat} data-etat="envoye">
                    <Icone nom="envoi" taille={12} /> envoyé
                  </span>
                )}
              </button>
            ))}
            {operativeProposed && !shadow && (
              <button
                type="button"
                className={`${mise.onglet} ${mise.ajout}`}
                title="Un acte a été détecté. Rédigé seulement à partir de ce qui a été dit pendant l’intervention."
                onClick={() =>
                  act(
                    `/encounters/${id}/documents/operative-note`,
                    undefined,
                    "Compte rendu de soins rédigé.",
                  )
                }
              >
                + Compte rendu de soins <small>un acte a été détecté</small>
              </button>
            )}
            {!shadow &&
              !docs.some((doc) => doc.document_type === "referral_letter") && (
                <button
                  type="button"
                  className={`${mise.onglet} ${mise.ajout}`}
                  title="Rédigé à partir de ce qui a été dit ; vous le complétez en écrivant dans le texte."
                  onClick={() =>
                    act(
                      `/encounters/${id}/documents/referral-letter`,
                      undefined,
                      "Courrier d’adressage rédigé : complétez la demande au confrère en écrivant dans le texte.",
                    )
                  }
                >
                  + Courrier d’adressage
                </button>
              )}
          </div>
        )}
      </header>

      <div className={mise.bandeaux}>
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

      {/* Traitement coupé net (Mac en veille) : la consultation resterait « en
          traitement » pour toujours. On propose de reprendre ; le serveur refuse s'il
          travaille encore (moins de 5 min). */}
      {(data.status === "processing" || data.status === "finalizing") && (
        <div className="banner banner-info" role="status">
          Oris prépare le dossier — vous pouvez passer au patient suivant, cette
          page s’actualise seule. Si rien ne bouge après cinq minutes,
          relancez : Oris reprend là où il s’était arrêté.{" "}
          <Bouton
            variante="secondaire"
            onClick={() =>
              act(`/encounters/${id}/process`, undefined, "Traitement relancé.")
            }
          >
            Relancer le traitement
          </Bouton>
        </div>
      )}
      {/* Un dossier « à relire » sans un seul fait n'a rien à relire : l'extraction a
          échoué sans le dire (09/10/2026, trente-trois minutes de parole). On ne laisse
          pas le praticien devant une page vide sans issue. */}
      {data.status === "review" &&
        object !== null &&
        object.facts.length === 0 &&
        object.procedures.length === 0 &&
        object.treatment_plan === null &&
        transcript.state === "ready" &&
        transcript.data.segments.length > 0 && (
          <div className="banner banner-review" role="alert">
            La consultation a bien été entendue et transcrite, mais Oris n’en a
            tiré aucune information clinique : il n’y a rien à relire.
            L’enregistrement et la transcription sont conservés.{" "}
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
      {data.processing_errors.some((e) => messageRegle(e.rule)) && (
        <div className="banner banner-review" role="alert">
          {data.processing_errors
            .map((e) => messageRegle(e.rule))
            .filter(Boolean)
            .join(" ")}
          {/* Rien n'a été entendu : rien à perdre, la consultation s'efface d'un geste. */}
          {data.processing_errors.some(
            (e) =>
              e.rule === "NO_TRANSCRIPT" ||
              e.rule === "AUDIO_SILENT" ||
              e.rule === "AUDIO_TEST_TONE",
          ) && (
            <div>
              <button
                type="button"
                className={styles.supprimerFort}
                disabled={suppression === "en_cours"}
                onClick={() => void supprimer()}
              >
                <Icone nom="corbeille" taille={15} /> Supprimer cette
                consultation
              </button>
            </div>
          )}
          {(data.processing_errors.some((e) => e.rule === "STT_UNAVAILABLE") ||
            data.status === "generation_failed") && (
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
      {data.processing_errors.some((e) => !messageRegle(e.rule)) && (
        <div className="banner banner-critical" role="alert">
          Oris a refusé le résultat de l’extraction plutôt que de le corriger en
          silence :{" "}
          {data.processing_errors
            .filter((e) => !messageRegle(e.rule))
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
      </div>

      <div className={mise.corps}>
        <section aria-label="Document">
          {docs.length === 0 && (
            <Carte>
              <p className="muted" style={{ margin: 0 }}>
                Aucun document pour cette consultation.
              </p>
            </Carte>
          )}

          {docs.length > 0 && active && (
            <article
              className={mise.feuille}
              role="tabpanel"
              aria-label={DOCUMENT_TYPE[active.document_type]}
            >
              {/* La barre du document : ce qu'on fait souvent, à plat ; le reste dans « ⋯ ». */}
              {!shadow && (
                <div className={mise.outils}>
                  {REDIGES.has(active.document_type) && (
                    <button
                      type="button"
                      className={mise.outilIa}
                      disabled={!corrigeable}
                      title="Claude relit le document et propose des améliorations, à cocher"
                      onClick={() => assistant.current?.relire()}
                    >
                      ✦ Relecture par Claude
                    </button>
                  )}
                  <button
                    type="button"
                    className={mise.outil}
                    onClick={() => void exportDocument(active)}
                  >
                    PDF
                  </button>
                  <button
                    type="button"
                    className={mise.outil}
                    onClick={() => void copyForRecord(active)}
                  >
                    Copier
                  </button>
                  <details className={mise.menu}>
                    <summary
                      title="Raccourcir, rédiger à nouveau, supprimer"
                      aria-label="Autres actions sur ce document"
                    >
                      ⋯
                    </summary>
                    <div className={mise.menuContenu}>
                      <button type="button" onClick={() => void raccourcir()}>
                        Raccourcir tous mes comptes rendus
                      </button>
                      {active.document_type !== "treatment_plan_text" && (
                        <button
                          type="button"
                          onClick={() =>
                            act(
                              `/documents/${active.id}/rediger`,
                              undefined,
                              "Document rédigé à nouveau depuis le dossier clinique.",
                            )
                          }
                        >
                          Rédiger à nouveau depuis le dossier
                        </button>
                      )}
                      <button
                        type="button"
                        data-danger="true"
                        onClick={() => setConfirmerRetrait(active.id)}
                      >
                        <Icone nom="corbeille" taille={15} /> Supprimer ce{" "}
                        {nomDocument}
                      </button>
                    </div>
                  </details>
                  <span
                    className={mise.etatTexte}
                    data-etat={etatTexte.etat}
                    role="status"
                  >
                    {etatTexte.etat === "saisie" && "Modification en cours…"}
                    {etatTexte.etat === "enregistrement" && "Enregistrement…"}
                    {etatTexte.etat === "enregistre" && "✓ Enregistré"}
                    {etatTexte.etat === "erreur" &&
                      `Non enregistré : ${etatTexte.message ?? ""}`}
                    {etatTexte.etat === "repos" &&
                      (valide
                        ? `Version ${active.version} · validée`
                        : active.document_type === "treatment_plan_text"
                          ? `Version ${active.version}`
                          : "Cliquez dans le texte pour le modifier")}
                  </span>
                </div>
              )}

              {/* Le correspondant se choisit ici : plus besoin d'ouvrir la fiche du patient. */}
              {!shadow && (
                <CorrespondantRapide
                  patientId={data.patient.id}
                  onChange={() => setVersionEnvoi((v) => v + 1)}
                />
              )}

              <div className={mise.page}>
                {confirmerRetrait === active.id && (
                  <div className="banner banner-critical" role="alertdialog">
                    Supprimer ce {nomDocument} ? Ses versions et ses envois
                    notés partent avec lui.
                    <Barre>
                      <button
                        type="button"
                        className={styles.supprimerFort}
                        onClick={() => void retirerDocument(active)}
                      >
                        Supprimer
                      </button>
                      <Bouton
                        variante="secondaire"
                        onClick={() => setConfirmerRetrait(null)}
                      >
                        Annuler
                      </Bouton>
                    </Barre>
                  </div>
                )}

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

                {active.document_type === "treatment_plan_text" && (
                  <PlanVisuel encounterId={id} version={active.version} />
                )}

                {active.document_type === "treatment_plan_text" && object && (
                  // Les outils du plan restent là, repliés : on lit d'abord, on corrige ensuite.
                  <details className={styles.corrigerPlan}>
                    <summary>
                      Modifier le plan (statuts, ordre, ajouts, retraits)
                    </summary>
                    <TreatmentPlanCards
                      encounter={data}
                      clinicalObject={object}
                      onSelectFact={(factId) =>
                        setSelection({ kind: "fact", factId })
                      }
                      onCorrected={reloadAll}
                    />
                  </details>
                )}

                {active.document_type !== "treatment_plan_text" && (
                  <TexteModifiable
                    key={`${active.id}-${active.version}`}
                    document={active}
                    modifiable={!shadow && !valide}
                    selected={
                      selection?.kind === "claim" ? selection.claim : null
                    }
                    onSelect={(claim) => setSelection({ kind: "claim", claim })}
                    onEtat={(etat, message) =>
                      setEtatTexte(message ? { etat, message } : { etat })
                    }
                    onEnregistre={() => {
                      reloadDocuments();
                      reloadLearning();
                    }}
                  />
                )}

                <div className={mise.sousTexte}>
                  {/* Claude n'a pas pu rédiger : Oris a posé sa version simplifiée. On le dit,
                      et on propose de réessayer — ce document seul, les autres ne bougent pas. */}
                  {active.generator.includes("(repli)") && !shadow && (
                    <div className="banner banner-review" role="status">
                      <strong>Version simplifiée.</strong> La rédaction par
                      Claude n’a pas abouti pour ce document ; Oris a posé sa
                      version de secours, fidèle mais télégraphique.{" "}
                      <Bouton
                        variante="secondaire"
                        onClick={() =>
                          act(
                            `/documents/${active.id}/rediger`,
                            undefined,
                            "Document rédigé à nouveau.",
                          )
                        }
                      >
                        Rédiger à nouveau
                      </Bouton>
                    </div>
                  )}

                  {active.generator.startsWith("practitioner") && (
                    <p className="muted" style={{ margin: 0 }}>
                      Texte écrit à la main : c’est le vôtre, Oris ne le
                      rattache plus phrase par phrase au dossier clinique. « ⋯ ›
                      Rédiger à nouveau » revient à la version d’Oris.
                    </p>
                  )}

                  {valide && active.document_type !== "treatment_plan_text" && (
                    <p className="muted" style={{ margin: 0 }}>
                      Document validé : il ne se modifie plus en cliquant
                      dedans. Une correction demandée à droite en rédige une
                      nouvelle version, à valider de nouveau.
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
                </div>
              </div>

              {/* Les photos restent sous le texte, avec leur glisser-déposer (Franck,
                  10/11/2026 : « il faut toujours le drag and drop photos sous le texte »). */}
              {!shadow && (
                <div className={mise.bloc}>
                  <Documentation
                    documentId={active.id}
                    patientId={data.patient.id}
                    encounterId={data.id}
                  />
                </div>
              )}

              {/* L'envoi vient après la validation : avant, il se replie pour ne pas
                  occuper un écran entier avec un formulaire qu'on ne peut pas envoyer. */}
              {!shadow && (
                <div className={mise.bloc} id="envoi">
                  {valide ? (
                    <>
                      <h2 className={mise.blocTitre}>
                        Envoyer ce {nomDocument}
                        {envoye && <small>déjà envoyé — voir plus bas</small>}
                      </h2>
                      <EnvoiDocument
                        key={versionEnvoi}
                        documentId={active.id}
                        version={active.version}
                        onEnvoye={reloadAll}
                        onEditer={() =>
                          window.scrollTo({ top: 0, behavior: "smooth" })
                        }
                        smilecloudRelie={Boolean(data.patient.smilecloud_case_id)}
                        valide={valide}
                      />
                      <Envois
                        documentId={active.id}
                        patientId={data.patient.id}
                        envois={envoisDe(active.id)}
                        onChange={reloadAll}
                      />
                    </>
                  ) : (
                    <details className={mise.avantValidation}>
                      <summary>
                        Envoi, impression, dépôt SmileCloud — après validation
                        (ouvrir quand même)
                      </summary>
                      <EnvoiDocument
                        key={versionEnvoi}
                        documentId={active.id}
                        version={active.version}
                        onEnvoye={reloadAll}
                        onEditer={() =>
                          window.scrollTo({ top: 0, behavior: "smooth" })
                        }
                        smilecloudRelie={Boolean(data.patient.smilecloud_case_id)}
                        valide={valide}
                      />
                      <Envois
                        documentId={active.id}
                        patientId={data.patient.id}
                        envois={envoisDe(active.id)}
                        onChange={reloadAll}
                      />
                    </details>
                  )}
                </div>
              )}
            </article>
          )}
        </section>

        {/* 4. À droite : corriger d'abord, vérifier ensuite, le reste rangé dessous. */}
        <aside className={mise.colonne}>
          {object && !shadow && (
            <AssistantCorrection
              ref={assistant}
              encounterId={data.id}
              documentId={active?.id ?? null}
              relisible={active ? REDIGES.has(active.document_type) : false}
              actif={corrigeable}
              civilite={data.patient.civility ?? ""}
              onChange={reloadAll}
            />
          )}

          {active && !shadow && !valide && criticalWarnings.length > 0 && (
            <label className={mise.accuse}>
              <input
                type="checkbox"
                checked={acknowledged}
                onChange={(event) => setAcknowledged(event.target.checked)}
              />
              J’ai pris connaissance de l’alerte critique : ce document n’est
              pas exhaustif.
            </label>
          )}

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

          {/* Le formulaire fait par fait reste là pour qui préfère cocher que dire. */}
          {object && !shadow && (
            <details className={mise.replie}>
              <summary>Corriger le dossier à la main</summary>
              <p className="muted" style={{ marginTop: 0 }}>
                Une correction modifie d’abord le dossier clinique ; Oris
                réécrit ensuite tous les documents.
              </p>
              <CorrectionPanel
                encounter={data}
                clinicalObject={object}
                onCorrected={reloadAll}
              />
            </details>
          )}

          {/* Les pièces du patient, ici et pas ailleurs : aller les voir obligeait à
              quitter le compte rendu, donc à perdre le fil (Franck, 10/10/2026). La
              récupération SmileCloud y est aussi, pour la même raison. Une pièce
              déposée ici est rattachée à cette consultation. */}
          <Carte
            titre="Bibliothèque"
            action={
              <Link
                href={`/patients/${data.patient.id}`}
                className="link-button"
              >
                fiche patient
              </Link>
            }
          >
            <SmileCloud
              patientId={data.patient.id}
              rapatries={() => setVersionPieces((v) => v + 1)}
            />
            <PiecesJointes
              key={versionPieces}
              patientId={data.patient.id}
              encounterId={data.id}
              compact
            />
          </Carte>

          {audio.state === "ready" && (
            <p className={mise.audio}>
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
      {toast && (
        <div className={styles.toast} role="status">
          <Icone nom="valide" taille={18} /> {toast}
        </div>
      )}
    </div>
  );
}
