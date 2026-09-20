"use client";

import { useApi } from "@/lib/useApi";

/** Vocabulaire d'Oris : un praticien ne doit jamais lire « cold_sensitivity ». */
export function useConcepts(): (concept: string) => string {
  const [concepts] = useApi<Record<string, string>>("/ontology/concepts");
  const table = concepts.state === "ready" ? concepts.data : {};
  return (concept: string) => table[concept] ?? concept.replace(/_/g, " ");
}
