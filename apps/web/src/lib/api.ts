import type { components } from "@/contracts/api";

/**
 * Client de l'API Oris. Les objets cliniques utilisent les types générés
 * (`@/contracts/generated`) ; les réponses techniques sont typées ici.
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_ORIS_API_URL ?? "http://localhost:8000";

export interface HealthResponse {
  status: "ok";
  service: "oris-api";
  version: string;
  environment: "local" | "test" | "staging" | "production";
  providers: {
    speech_to_text: string;
    clinical_extraction: string;
    document_generation: string;
    clinical_validation: string;
  };
}

export type ApiHealth =
  | { state: "reachable"; health: HealthResponse }
  | { state: "unreachable" };

function isHealthResponse(value: unknown): value is HealthResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    candidate.status === "ok" &&
    candidate.service === "oris-api" &&
    typeof candidate.version === "string" &&
    typeof candidate.providers === "object" &&
    candidate.providers !== null
  );
}

export async function fetchHealth(
  fetcher: typeof fetch = fetch,
  baseUrl: string = API_BASE_URL,
): Promise<ApiHealth> {
  try {
    const response = await fetcher(`${baseUrl}/health`, { cache: "no-store" });
    if (!response.ok) return { state: "unreachable" };
    const body: unknown = await response.json();
    return isHealthResponse(body) ? { state: "reachable", health: body } : { state: "unreachable" };
  } catch {
    return { state: "unreachable" };
  }
}

// --- Routes métier : types générés depuis packages/openapi/openapi.json -----------


type Schemas = components["schemas"];
export type Patient = Schemas["PatientOut"];
/** Le patient **dans la liste** : avec de quoi le reconnaître sans l'ouvrir. */
export type PatientListe = Schemas["PatientListOut"];
export type Encounter = Schemas["EncounterOut"];
export type DocumentView = Schemas["DocumentOut"];
export type Claim = Schemas["ClaimOut"];
export type ClinicalObjectView = Schemas["ClinicalObjectOut"];
export type ClinicalObject = Schemas["ClinicalEncounter"];
export type ClinicalFactView = ClinicalObject["facts"][number];
export type TranscriptView = Schemas["TranscriptOut"];
export type LearningEventView = Schemas["LearningEventOut"];
export type SyntheticCase = Schemas["SyntheticCaseOut"];
export type CorrectionRequest = Schemas["CorrectionRequest"];

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    readonly details: string[] = [],
  ) {
    super(code);
  }
}

export async function apiRequest<T>(
  path: string,
  init: { method?: "GET" | "POST" | "PATCH" | "DELETE"; body?: unknown } = {},
  fetcher: typeof fetch = fetch,
  baseUrl: string = API_BASE_URL,
): Promise<T> {
  let response: Response;
  try {
    response = await fetcher(`${baseUrl}${path}`, {
      method: init.method ?? "GET",
      cache: "no-store",
      headers: init.body === undefined ? {} : { "Content-Type": "application/json" },
      ...(init.body === undefined ? {} : { body: JSON.stringify(init.body) }),
    });
  } catch {
    throw new ApiError(0, "NETWORK_UNREACHABLE");
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const error = (body ?? {}) as { code?: unknown; details?: unknown };
    throw new ApiError(
      response.status,
      typeof error.code === "string" ? error.code : `HTTP_${response.status}`,
      Array.isArray(error.details) ? error.details.filter((d): d is string => typeof d === "string") : [],
    );
  }
  return body as T;
}

export type ExportFormat = "pdf" | "text" | "structured";

export type DocumentExport = { blob: Blob; filename: string };

/** Sortie d'un document : le serveur renvoie un fichier, pas du JSON. */
export async function fetchDocumentExport(
  documentId: string,
  format: ExportFormat,
  fetcher: typeof fetch = fetch,
  baseUrl: string = API_BASE_URL,
): Promise<DocumentExport> {
  let response: Response;
  try {
    response = await fetcher(`${baseUrl}/documents/${documentId}/export?format=${format}`, {
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "NETWORK_UNREACHABLE");
  }
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const error = (body ?? {}) as { code?: unknown };
    throw new ApiError(
      response.status,
      typeof error.code === "string" ? error.code : `HTTP_${response.status}`,
    );
  }
  return { blob: await response.blob(), filename: filenameFrom(response) };
}

function filenameFrom(response: Response): string {
  const disposition = response.headers.get("content-disposition") ?? "";
  return /filename="([^"]+)"/.exec(disposition)?.[1] ?? "document";
}

export type ClientConfig = Schemas["ClientConfigOut"];
/** Pièce jointe importée : photo, radio, empreinte. Oris ne la lit pas (§55). */
export type Attachment = Schemas["AttachmentOut"];
/** Point marqué pendant l'écoute : un instant retenu, pas une donnée clinique (§11). */
export type Mark = Schemas["MarkOut"];
export type AudioSessionView = Schemas["AudioSessionOut"];

export type SpokenCorrection = Schemas["SpokenCorrectionOut"];

/** Correction dictée au micro : le son part dans la requête, il n'est pas stocké. */
export async function sendVoiceCorrection(
  encounterId: string,
  pcm: Uint8Array,
  options: { apply?: boolean; expectedObjectVersion?: number } = {},
  fetcher: typeof fetch = fetch,
  baseUrl: string = API_BASE_URL,
): Promise<SpokenCorrection> {
  const query = new URLSearchParams();
  if (options.apply) query.set("apply", "true");
  if (options.expectedObjectVersion !== undefined) {
    query.set("expected_object_version", String(options.expectedObjectVersion));
  }
  let response: Response;
  try {
    response = await fetcher(
      `${baseUrl}/encounters/${encounterId}/corrections/voice?${query.toString()}`,
      {
        method: "POST",
        headers: { "Content-Type": "audio/pcm;rate=16000;channels=1;encoding=s16le" },
        body: pcm as BodyInit,
      },
    );
  } catch {
    throw new ApiError(0, "NETWORK_UNREACHABLE");
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const error = (body ?? {}) as { code?: unknown };
    throw new ApiError(
      response.status,
      typeof error.code === "string" ? error.code : `HTTP_${response.status}`,
    );
  }
  return body as SpokenCorrection;
}

export type Preferences = Schemas["PractitionerPreferences"];
export type GlossaryTerm = Schemas["GlossaryTermOut"];
export type LearningSuggestion = Schemas["SuggestionOut"];
export type FrequentCorrection = Schemas["FrequentCorrectionOut"];
export type LearningExport = Schemas["LearningExport"];
/** Moteur qui a réellement tourné, et la consigne qui l'accompagnait (§202). */
export type EngineVersion = Schemas["EngineVersionOut"];
/** Ce qu'Oris entend pendant la consultation : provisoire, jamais le dossier (§14.1). */
export type LiveTranscript = Schemas["LiveTranscriptOut"];

export type Progress = Schemas["ProgressOut"];

export type Cabinet = Schemas["CabinetOut"];

/** L'agenda du jour, repris de Dental Lens (écran « Votre journée »). */
export type Journee = Schemas["JourneeOut"];
export type RendezVous = Schemas["RendezVousOut"];
export type Jour = Schemas["JourOut"];

/** Carnet d'adresses : confrères et structures à qui l'on adresse un patient. */
export type Correspondant = Schemas["CorrespondentOut"];

/** Le lien entre un patient et un correspondant, et ce qu'il veut dire. */
export type Rattachement = Schemas["RattachementOut"];
