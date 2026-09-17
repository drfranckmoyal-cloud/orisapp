"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, apiRequest, type Encounter, type Patient, type SyntheticCase } from "@/lib/api";
import { DOMAIN, errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

export default function NewConsultationPage() {
  const router = useRouter();
  const [cases] = useApi<SyntheticCase[]>("/synthetic-cases");
  const [patients] = useApi<Patient[]>("/patients");
  const [patientId, setPatientId] = useState("");

  async function prepareListening() {
    setError(null);
    try {
      const encounter = await apiRequest<Encounter>("/encounters", {
        method: "POST",
        body: { patient_id: patientId },
      });
      router.push(`/consultations/${encounter.id}/ecoute`);
    } catch (caught) {
      setError(errorMessage(caught instanceof ApiError ? caught.code : "UNKNOWN"));
    }
  }
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

      <section className="card" aria-labelledby="micro-heading">
        <h2 id="micro-heading">Consultation au micro</h2>
        <p className="muted">
          L’audio est capté, envoyé et contrôlé. La transcription automatique n’est pas encore
          branchée (étape M4) : aucun document ne sera rédigé à partir du micro pour l’instant.
        </p>
        {patients.state === "ready" && patients.data.length === 0 ? (
          <p className="muted">
            Aucun patient : <Link href="/patients">créez d’abord un patient fictif</Link>.
          </p>
        ) : (
          <div className="form-row">
            <label className="field">
              Patient
              <select className="input" value={patientId} onChange={(event) => setPatientId(event.target.value)}>
                <option value="">Choisir…</option>
                {patients.state === "ready" &&
                  patients.data.map((patient) => (
                    <option key={patient.id} value={patient.id}>
                      {patient.last_name} {patient.first_name}
                    </option>
                  ))}
              </select>
            </label>
            <button type="button" className="button button-primary" disabled={!patientId} onClick={prepareListening}>
              Préparer l’écoute
            </button>
          </div>
        )}
      </section>

      <div className="banner banner-info">
        Démonstration : choisissez une consultation fictive du corpus. Oris la traite comme une
        vraie (transcription, faits, documents).
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
