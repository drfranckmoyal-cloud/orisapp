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
  init: { method?: "GET" | "POST" | "PATCH"; body?: unknown } = {},
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
