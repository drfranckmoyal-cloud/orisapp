"use client";

import { type FormEvent, useState } from "react";

import { ApiError, apiRequest, type ClinicalObject, type CorrectionRequest, type Encounter } from "@/lib/api";
import { PLAN_STATUS, errorMessage } from "@/lib/labels";

type Operation = CorrectionRequest["operations"][number];
type PlanStatus = keyof typeof PLAN_STATUS;

/** Corrections cliniques : modifient l'objet, puis Oris régénère les documents (D016). */
export function CorrectionPanel({
  encounter,
  clinicalObject,
  onCorrected,
}: {
  encounter: Encounter;
  clinicalObject: ClinicalObject;
  onCorrected: () => void;
}) {
  const [message, setMessage] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const teeth = [...new Set(clinicalObject.facts.flatMap((fact) => fact.teeth))].sort();

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
      const details = error instanceof ApiError && error.details.length ? ` (${error.details.join(", ")})` : "";
      setMessage({ tone: "error", text: errorMessage(code) + details });
    } finally {
      setBusy(false);
    }
  }

  function replaceTooth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    void submit({
      operation: "replace_tooth",
      from_tooth: String(data.get("from_tooth")),
      to_tooth: String(data.get("to_tooth")),
    });
  }

  const correctable = ["review", "validated", "exported"].includes(encounter.status);

  return (
    <div style={{ display: "grid", gap: 16 }}>
      {teeth.length > 0 && (
        <form className="form-row" onSubmit={replaceTooth} aria-label="Remplacer une dent">
          <label className="field">
            Remplacer la dent
            <select className="input" name="from_tooth" defaultValue={teeth[0]}>
              {teeth.map((tooth) => (
                <option key={tooth}>{tooth}</option>
              ))}
            </select>
          </label>
          <label className="field">
            par
            <input
              className="input"
              name="to_tooth"
              required
              inputMode="numeric"
              pattern="^(1[1-8]|2[1-8]|3[1-8]|4[1-8]|5[1-5]|6[1-5]|7[1-5]|8[1-5])$"
              title="Numéro de dent FDI, par exemple 27"
              size={4}
            />
          </label>
          <button type="submit" className="button button-primary" disabled={busy || !correctable}>
            Corriger
          </button>
        </form>
      )}

      {clinicalObject.treatment_plan?.items.map((item) => (
        <label key={item.item_id} className="field">
          {item.teeth.length > 0 ? `${item.teeth.join(", ")} — ` : ""}
          {item.action}
          <select
            className="input"
            value={item.status}
            disabled={busy || !correctable}
            onChange={(event) =>
              void submit({
                operation: "set_plan_item_status",
                item_id: item.item_id,
                status: event.target.value as PlanStatus,
              })
            }
          >
            {(Object.keys(PLAN_STATUS) as PlanStatus[]).map((status) => (
              <option key={status} value={status}>
                Statut : {PLAN_STATUS[status]}
              </option>
            ))}
          </select>
        </label>
      ))}

      {message && (
        <div className={`banner ${message.tone === "ok" ? "banner-info" : "banner-critical"}`} role="status">
          {message.text}
        </div>
      )}
    </div>
  );
}
