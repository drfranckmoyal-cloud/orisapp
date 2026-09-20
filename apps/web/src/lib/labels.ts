/** Libellés français de l'interface. Les valeurs viennent des contrats générés. */

import type { ClinicalFactView, DocumentView, Encounter } from "./api";

export const ENCOUNTER_STATUS: Record<Encounter["status"], string> = {
  draft: "Brouillon",
  recording: "En écoute",
  paused: "En pause",
  finalizing: "Finalisation",
  processing: "Traitement en cours",
  review: "À valider",
  validated: "Validée",
  exported: "Exportée",
  archived: "Archivée",
  audio_error: "Erreur audio",
  upload_interrupted: "Envoi interrompu",
  transcription_failed: "Transcription impossible",
  generation_failed: "Extraction refusée",
};

export const DOCUMENT_STATUS: Record<DocumentView["status"], string> = {
  draft_ai: "Brouillon Oris",
  needs_review: "À vérifier",
  validated: "Validé",
  exported: "Exporté",
  superseded: "Remplacé",
  outdated: "Périmé",
};

export const DOCUMENT_TYPE: Record<DocumentView["document_type"], string> = {
  consultation_note: "Compte rendu",
  treatment_plan_text: "Plan de traitement",
  operative_note: "Opératoire",
  patient_summary: "Résumé patient",
  referral_letter: "Courrier",
};

export const ASSERTION: Record<ClinicalFactView["assertion"], string> = {
  present: "présent",
  absent: "absent",
  uncertain: "incertain",
};

export const TEMPORALITY: Record<ClinicalFactView["temporality"], string> = {
  past: "passé",
  current: "actuel",
  future: "futur",
};

export const CLINICAL_STATUS: Record<ClinicalFactView["clinical_status"], string> = {
  patient_reported: "rapporté par le patient",
  observed: "constaté",
  clinician_assessment: "évaluation du praticien",
  differential: "hypothèse",
  discussed: "discuté",
  proposed: "proposé",
  accepted: "accepté",
  refused: "refusé",
  deferred: "reporté",
  planned: "prévu",
  performed: "réalisé",
};

export const CERTAINTY: Record<ClinicalFactView["certainty"], string> = {
  certain: "certain",
  probable: "probable",
  possible: "possible",
  unknown: "indéterminé",
};

export const SPEAKER: Record<string, string> = {
  practitioner: "Praticien",
  patient: "Patient",
  assistant: "Assistante",
  companion: "Accompagnant",
  unknown: "Inconnu",
  manual: "Saisie manuelle",
};

export const PLAN_STATUS = {
  discussed: "discuté",
  proposed: "proposé",
  accepted: "accepté",
  refused: "refusé",
  deferred: "reporté",
  planned: "prévu",
  completed: "réalisé",
} as const;

export const DOMAIN: Record<string, string> = {
  aesthetic_consultation: "Consultation esthétique",
  tooth_wear_consultation: "Usures dentaires",
  composite_procedure: "Composite",
  veneer_procedure: "Facettes",
  extraction_procedure: "Extraction",
  adversarial: "Cas pièges",
};

export const LEARNING_EVENT: Record<string, string> = {
  tooth_number_correction: "Numéro de dent corrigé",
  negation_correction: "Négation corrigée",
  temporality_correction: "Temporalité corrigée",
  certainty_correction: "Certitude corrigée",
  treatment_status_correction: "Statut de traitement corrigé",
  clinical_fact_added: "Fait ajouté",
  clinical_fact_removed: "Fait retiré",
  clinical_fact_corrected: "Fait corrigé",
  warning_confirmed: "Alerte reconnue",
  document_validated_unchanged: "Document validé sans modification",
};

const ERRORS: Record<string, string> = {
  NETWORK_UNREACHABLE: "Serveur Oris injoignable.",
  MICROPHONE_UNAVAILABLE: "Micro indisponible : autorisez-le dans le navigateur.",
  OBJECT_VERSION_REQUIRED: "Rechargez la page avant d’appliquer cette correction.",
  STT_UNAVAILABLE: "La transcription est indisponible : réessayez dans un instant.",
  NO_PROCEDURE_TO_DOCUMENT: "Aucun acte n’a été dit : il n’y a pas de compte rendu de soins à rédiger.",
  DOCUMENT_EMPTY: "Ce document n’a pas encore de contenu.",
  DOCUMENT_NOT_FOUND: "Ce document est introuvable.",
  COPY_FAILED: "La copie a échoué : votre navigateur l’a refusée.",
  DOCUMENT_OUTDATED: "Ce document est périmé : régénérez-le avant de le valider.",
  DOCUMENT_HAS_CRITICAL_ISSUES: "Le document contient une phrase non justifiée : validation impossible.",
  WARNING_NOT_ACKNOWLEDGED: "Confirmez d’abord avoir pris connaissance de l’alerte critique.",
  DOCUMENT_ALREADY_VALIDATED: "Ce document est déjà validé.",
  DOCUMENTS_NOT_VALIDATED: "Tous les documents doivent être validés avant la consultation.",
  OBJECT_VERSION_CONFLICT: "La consultation a été modifiée entre-temps : rechargez la page.",
  CORRECTION_REJECTED: "Correction refusée : elle rendrait le dossier incohérent.",
  TOOTH_NOT_FOUND: "Aucun élément ne porte cette dent.",
  SAME_TOOTH: "Les deux numéros de dent sont identiques.",
  NO_CHANGE: "Aucune modification à enregistrer.",
  FACT_REFERENCED: "Ce fait appuie le plan de traitement : modifiez d’abord le plan.",
  INVALID_TRANSITION: "Cette action n’est pas possible dans l’état actuel de la consultation.",
  PATIENT_INFORMATION_REQUIRED: "Confirmez d’abord que le patient a été informé de l’enregistrement.",
  AUDIO_CHUNKS_MISSING: "Des segments audio ne sont pas arrivés au serveur.",
  insecure_context: "Le micro n’est accessible que sur une connexion sécurisée (https).",
  unsupported: "Ce navigateur ne permet pas la capture du micro.",
  permission_denied:
    "L’accès au micro a été refusé. Autorisez-le dans les réglages du navigateur (icône à gauche de l’adresse), puis réessayez.",
  no_microphone: "Aucun micro détecté. Branchez un micro puis réessayez.",
  microphone_busy: "Le micro est déjà utilisé par une autre application.",
  capture_failed: "La capture audio n’a pas pu démarrer.",
  microphone_lost: "Le micro a été coupé ou débranché. La partie non captée sera signalée.",
};

export const PROCESSING_RULE: Record<string, string> = {
  STT_UNAVAILABLE:
    "Le service de transcription n’a pas répondu. L’audio est conservé : relancez le traitement plus tard.",
  NO_TRANSCRIPT:
    "Aucune parole n’a été reconnue dans l’enregistrement : rien n’a pu être rédigé. Vérifiez que le micro capte bien les deux voix, puis refaites un essai.",
  SPEAKER_ROLES_UNKNOWN:
    "Les voix n’ont pas pu être attribuées avec certitude : vérifiez qui a dit quoi.",
};

export function formatDuration(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const pad = (value: number) => String(value).padStart(2, "0");
  return hours > 0 ? `${hours}:${pad(minutes)}:${pad(seconds)}` : `${pad(minutes)}:${pad(seconds)}`;
}

export function errorMessage(code: string): string {
  return ERRORS[code] ?? `Action impossible (${code}).`;
}

export function formatDateTime(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short" }).format(
    new Date(value),
  );
}

export function formatClock(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

const AXIS_LABELS: Record<string, Record<string, string>> = {
  teeth: {},
  status: PLAN_STATUS,
  assertion: ASSERTION,
  temporality: TEMPORALITY,
  certainty: CERTAINTY,
  clinical_status: CLINICAL_STATUS,
};

function side(payload: unknown, field: string): string | null {
  if (payload === null || typeof payload !== "object") return null;
  const value = (payload as Record<string, unknown>)[field];
  if (Array.isArray(value)) return value.length > 0 ? value.join(", ") : "aucune";
  if (typeof value !== "string") return null;
  return AXIS_LABELS[field]?.[value] ?? value;
}

/** Ce qu'une correction a changé, en toutes lettres : « 26 → 27 ». */
export function correctionDetail(event: {
  before: unknown;
  after: unknown;
}): string | null {
  for (const field of ["teeth", "status", "assertion", "temporality", "certainty", "clinical_status"]) {
    const before = side(event.before, field);
    const after = side(event.after, field);
    if (before !== null && after !== null && before !== after) {
      return `${before} → ${after}`;
    }
  }
  return null;
}

/** Date seule, format français. */
export function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}
