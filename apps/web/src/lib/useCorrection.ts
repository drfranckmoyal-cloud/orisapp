"use client";

import { useState } from "react";

import {
  ApiError,
  apiRequest,
  type ClinicalObject,
  type CorrectionRequest,
  type Encounter,
} from "@/lib/api";
import { errorMessage } from "@/lib/labels";

export type Operation = CorrectionRequest["operations"][number];
export type CorrectionMessage = { tone: "ok" | "error"; text: string };

/** Une correction modifie d'abord le dossier clinique ; Oris réécrit ensuite (D016).
 *
 * Mutualisé entre les écrans qui corrigent (dent, statut de plan) : la règle de
 * version attendue et le message au praticien doivent être les mêmes partout.
 */
export function useCorrection(
  encounter: Encounter,
  clinicalObject: ClinicalObject,
  onCorrected: () => void,
) {
  const [message, setMessage] = useState<CorrectionMessage | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(operation: Operation) {
    setBusy(true);
    setMessage(null);
    try {
      const updated = await apiRequest<Encounter>(`/encounters/${encounter.id}/clinical-object`, {
        method: "PATCH",
        body: {
          expected_object_version: clinicalObject.object_version,
          operations: [operation],
          regenerate: true,
        } satisfies CorrectionRequest,
      });
      setMessage({
        tone: "ok",
        text: `Dossier clinique mis à jour (version ${updated.object_version}), documents régénérés. Correction enregistrée.`,
      });
      onCorrected();
    } catch (error) {
      const code = error instanceof ApiError ? error.code : "UNKNOWN";
      const details =
        error instanceof ApiError && error.details.length ? ` (${error.details.join(", ")})` : "";
      setMessage({ tone: "error", text: errorMessage(code) + details });
    } finally {
      setBusy(false);
    }
  }

  // Corriger n'a de sens qu'une fois le dossier constitué ; un document déjà validé
  // ou exporté reste corrigible (il repassera en brouillon régénéré).
  const correctable = ["review", "validated", "exported"].includes(encounter.status);

  return { submit, busy, message, correctable };
}
