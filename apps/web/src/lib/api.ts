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
