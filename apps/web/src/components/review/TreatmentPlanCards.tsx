"use client";

import { useState } from "react";

import { Barre, Bouton, Champ } from "@/components/ui";
import type { ClinicalObject, Encounter } from "@/lib/api";
import { PLAN_STATUS } from "@/lib/labels";
import { useCorrection } from "@/lib/useCorrection";

type PlanItem = NonNullable<ClinicalObject["treatment_plan"]>["items"][number];
type PlanStatus = keyof typeof PLAN_STATUS;

const STATUS_TONE: Record<PlanStatus, string> = {
  discussed: "",
  proposed: "",
  accepted: "chip-success",
  refused: "chip-critical",
  deferred: "chip-review",
  planned: "chip-review",
  completed: "chip-success",
};

function factLabel(fact: ClinicalObject["facts"][number]): string {
  const teeth = fact.teeth.length > 0 ? ` (${fact.teeth.join(", ")})` : "";
  return `${typeof fact.value === "string" && fact.value ? fact.value : fact.concept}${teeth}`;
}

/** Le plan de traitement carte par carte : ce qui est proposé, pourquoi, où ça en est.
 *
 * Le statut se change ici, à l'endroit où on le lit — et c'est bien le dossier
 * clinique qui est modifié, jamais le texte du document.
 */
export function TreatmentPlanCards({
  encounter,
  clinicalObject,
  onSelectFact,
  onCorrected,
}: {
  encounter: Encounter;
  clinicalObject: ClinicalObject;
  onSelectFact: (factId: string) => void;
  onCorrected: () => void;
}) {
  const { submit, busy, message, correctable } = useCorrection(
    encounter,
    clinicalObject,
    onCorrected,
  );
  const [ajout, setAjout] = useState("");
  const plan = clinicalObject.treatment_plan;

  function deplacer(itemId: string, sens: -1 | 1) {
    if (plan === null) return;
    const ordre = ordonnes.map((item) => item.item_id);
    const index = ordre.indexOf(itemId);
    const cible = index + sens;
    if (cible < 0 || cible >= ordre.length) return;
    [ordre[index], ordre[cible]] = [ordre[cible]!, ordre[index]!];
    void submit({ operation: "reorder_plan_items", item_ids: ordre });
  }

  if (plan === null || plan.items.length === 0) {
    return <p className="muted">Aucun élément de plan n’a été énoncé pendant la consultation.</p>;
  }
  const byId = new Map(clinicalObject.facts.map((fact) => [fact.fact_id, fact]));
  // L'ordre n'est numéroté que si la séquence a été dite (§33.3).
  const ordonnes = [...plan.items].sort(
    (a: PlanItem, b: PlanItem) =>
      Number(a.sequence === null) - Number(b.sequence === null) ||
      (a.sequence ?? 0) - (b.sequence ?? 0),
  );
  const items = ordonnes;

  return (
    <div style={{ display: "grid", gap: 12 }}>
      {items.map((item) => (
        <article
          key={item.item_id}
          className="card"
          style={{ gap: 8, padding: "var(--space-16)" }}
          aria-label={item.action}
        >
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            {item.sequence !== null && <span className="chip">étape {item.sequence}</span>}
            {item.teeth.length > 0 && <span className="chip">dent {item.teeth.join(", ")}</span>}
            <strong style={{ fontSize: 16 }}>{item.action}</strong>
            <span className={`chip ${STATUS_TONE[item.status]}`}>{PLAN_STATUS[item.status]}</span>
          </div>

          {item.problem !== null && <p style={{ margin: 0 }}>Motif : {item.problem}</p>}

          {item.evidence_fact_ids.length > 0 && (
            <p style={{ margin: 0 }}>
              Pourquoi :{" "}
              {item.evidence_fact_ids.map((factId, index) => {
                const fact = byId.get(factId);
                return (
                  <span key={factId}>
                    {index > 0 && ", "}
                    <button
                      type="button"
                      className={"link-button"}
                      onClick={() => onSelectFact(factId)}
                    >
                      {fact ? factLabel(fact) : factId}
                    </button>
                  </span>
                );
              })}
            </p>
          )}

          {item.alternatives.length > 0 && (
            <p className="muted" style={{ margin: 0 }}>
              Alternatives évoquées : {item.alternatives.join(", ")}.
            </p>
          )}
          {item.prerequisites.length > 0 && (
            <p className="muted" style={{ margin: 0 }}>
              Préalables : {item.prerequisites.join(", ")}.
            </p>
          )}
          {item.uncertainties.length > 0 && (
            <p className="muted" style={{ margin: 0 }}>
              Incertitudes : {item.uncertainties.join(", ")}.
            </p>
          )}

          <Barre>
            <Bouton
              variante="discret"
              disabled={busy || !correctable}
              aria-label="Monter cet élément"
              onClick={() => deplacer(item.item_id, -1)}
            >
              ↑
            </Bouton>
            <Bouton
              variante="discret"
              disabled={busy || !correctable}
              aria-label="Descendre cet élément"
              onClick={() => deplacer(item.item_id, 1)}
            >
              ↓
            </Bouton>
            <Bouton
              variante="discret"
              disabled={busy || !correctable}
              onClick={() =>
                void submit({ operation: "remove_plan_item", item_id: item.item_id })
              }
            >
              Retirer
            </Bouton>
          </Barre>

          <label className="field" style={{ maxWidth: 320 }}>
            Statut
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
                  {PLAN_STATUS[status]}
                </option>
              ))}
            </select>
          </label>
        </article>
      ))}

      <form
        className="form-row"
        onSubmit={(event) => {
          event.preventDefault();
          if (!ajout.trim()) return;
          void submit({
            operation: "add_plan_item",
            action: ajout.trim(),
            teeth: [],
            status: "proposed",
          });
          setAjout("");
        }}
      >
        <label className="field" style={{ minWidth: 260 }}>
          Ajouter un traitement au plan
          <Champ
            value={ajout}
            placeholder="gouttière de protection"
            disabled={busy || !correctable}
            onChange={(event) => setAjout(event.target.value)}
          />
        </label>
        <Bouton type="submit" variante="secondaire" disabled={busy || !correctable || !ajout.trim()}>
          Ajouter
        </Bouton>
      </form>

      {message && (
        <div
          className={`banner ${message.tone === "ok" ? "banner-info" : "banner-critical"}`}
          role="status"
        >
          {message.text}
        </div>
      )}
    </div>
  );
}
