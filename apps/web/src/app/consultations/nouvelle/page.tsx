"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, apiRequest, type Encounter, type SyntheticCase } from "@/lib/api";
import { DOMAIN, errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

export default function NewConsultationPage() {
  const router = useRouter();
  const [cases] = useApi<SyntheticCase[]>("/synthetic-cases");
  const [running, setRunning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(caseId: string) {
    setRunning(caseId);
    setError(null);
    try {
      const encounter = await apiRequest<Encounter>(`/synthetic-cases/${caseId}/encounters`, {
        method: "POST",
      });
      router.push(`/consultations/${encounter.id}`);
    } catch (caught) {
      setError(errorMessage(caught instanceof ApiError ? caught.code : "UNKNOWN"));
      setRunning(null);
    }
  }

  const grouped = new Map<string, SyntheticCase[]>();
  if (cases.state === "ready") {
    for (const item of cases.data) {
      grouped.set(item.domain, [...(grouped.get(item.domain) ?? []), item]);
    }
  }

  return (
    <div className="page">
      <header>
        <h1>Nouvelle consultation</h1>
        <p className="subtitle">Mode démonstration</p>
      </header>

      <div className="banner banner-info">
        L’écoute par micro arrive à l’étape suivante. En attendant, choisissez une consultation
        fictive du corpus : Oris la traite comme une vraie (transcription, faits, documents).
      </div>

      {error && (
        <div className="banner banner-critical" role="alert">
          {error}
        </div>
      )}
      {cases.state === "loading" && <p className="muted">Chargement…</p>}
      {cases.state === "error" && <p className="muted">{errorMessage(cases.code)}</p>}

      {[...grouped.entries()].map(([domain, items]) => (
        <section key={domain} className="card" aria-labelledby={`domain-${domain}`}>
          <h2 id={`domain-${domain}`}>{DOMAIN[domain] ?? domain}</h2>
          <table className="table">
            <tbody>
              {items.map((item) => (
                <tr key={item.case_id}>
                  <td>{item.case_id}</td>
                  <td>
                    {item.patient_first_name} {item.patient_last_name}
                  </td>
                  <td>
                    {item.tags.map((tag) => (
                      <span key={tag} className="chip" style={{ marginRight: 4 }}>
                        {tag}
                      </span>
                    ))}
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <button
                      type="button"
                      className="button button-secondary"
                      disabled={running !== null}
                      onClick={() => run(item.case_id)}
                    >
                      {running === item.case_id ? "Traitement…" : "Lancer"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
    </div>
  );
}
