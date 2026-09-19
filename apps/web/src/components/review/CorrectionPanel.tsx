"use client";

import type { FormEvent } from "react";

import type { ClinicalObject, Encounter } from "@/lib/api";
import { useCorrection } from "@/lib/useCorrection";

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
  const { submit, busy, message, correctable } = useCorrection(
    encounter,
    clinicalObject,
    onCorrected,
  );
  const teeth = [...new Set(clinicalObject.facts.flatMap((fact) => fact.teeth))].sort();

  function replaceTooth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    void submit({
      operation: "replace_tooth",
      from_tooth: String(data.get("from_tooth")),
      to_tooth: String(data.get("to_tooth")),
    });
  }

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

      <p className="muted">
        Le statut d’un traitement se change sur sa carte, dans l’onglet « Plan de
        traitement ».
      </p>

      {message && (
        <div className={`banner ${message.tone === "ok" ? "banner-info" : "banner-critical"}`} role="status">
          {message.text}
        </div>
      )}
    </div>
  );
}
