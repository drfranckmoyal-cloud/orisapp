"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  ApiError,
  apiRequest,
  type Encounter,
  type Patient,
  type SyntheticCase,
} from "@/lib/api";
import { DOMAIN, errorMessage } from "@/lib/labels";
import { useApi } from "@/lib/useApi";

/** Démarrer une consultation : un nom, un bouton, l'écoute. Rien d'autre à décider. */
export default function NewConsultationPage() {
  const router = useRouter();
  const [cases] = useApi<SyntheticCase[]>("/synthetic-cases");
  const [patients] = useApi<Patient[]>("/patients");
  const [prenom, setPrenom] = useState("");
  const [nom, setNom] = useState("");
  const [patientChoisi, setPatientChoisi] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function startListening() {
    setBusy(true);
    setError(null);
    try {
      const patientId =
        patientChoisi ||
        (
          await apiRequest<Patient>("/patients", {
            method: "POST",
            body: {
              first_name: prenom.trim() || "Patient",
              last_name: nom.trim() || "Test",
            },
          })
        ).id;
      const encounter = await apiRequest<Encounter>("/encounters", {
        method: "POST",
        body: { patient_id: patientId },
      });
      router.push(`/consultations/${encounter.id}/ecoute`);
    } catch (caught) {
      setError(errorMessage(caught instanceof ApiError ? caught.code : "UNKNOWN"));
      setBusy(false);
    }
  }

  async function runSynthetic(caseId: string) {
    setBusy(true);
    setError(null);
    try {
      const encounter = await apiRequest<Encounter>(`/synthetic-cases/${caseId}/encounters`, {
        method: "POST",
      });
      router.push(`/consultations/${encounter.id}`);
    } catch (caught) {
      setError(errorMessage(caught instanceof ApiError ? caught.code : "UNKNOWN"));
      setBusy(false);
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
      <header className="page-header">
        <div>
          <p className="subtitle">Données fictives uniquement</p>
          <h1>Démarrer une consultation</h1>
        </div>
      </header>

      <section className="card" aria-labelledby="micro-heading">
        <h2 id="micro-heading">Au micro</h2>
        <p className="muted">
          Oris écoute, transcrit, puis rédige le compte rendu. Le son est supprimé dès que
          la transcription a abouti.
        </p>
        <form
          className="form-row"
          onSubmit={(event) => {
            event.preventDefault();
            void startListening();
          }}
        >
          {patients.state === "ready" && patients.data.length > 0 && (
            <label className="field" style={{ minWidth: 240 }}>
              Patient suivi
              <select
                className="input"
                value={patientChoisi}
                onChange={(event) => setPatientChoisi(event.target.value)}
              >
                <option value="">Nouveau patient…</option>
                {patients.data.map((patient) => (
                  <option key={patient.id} value={patient.id}>
                    {patient.first_name} {patient.last_name}
                  </option>
                ))}
              </select>
            </label>
          )}
          {!patientChoisi && (
            <>
              <label className="field">
                Prénom
                <input
                  className="input"
                  value={prenom}
                  placeholder="Patient"
                  autoFocus
                  onChange={(event) => setPrenom(event.target.value)}
                />
              </label>
              <label className="field">
                Nom
                <input
                  className="input"
                  value={nom}
                  placeholder="Test"
                  onChange={(event) => setNom(event.target.value)}
                />
              </label>
            </>
          )}
          <button type="submit" className="button button-large" disabled={busy}>
            {busy ? "Préparation…" : "Démarrer l’écoute"}
          </button>
        </form>
        {error && (
          <div className="banner banner-critical" role="alert">
            {error}
          </div>
        )}
      </section>

      <details className="card">
        <summary>
          <strong>Essayer sans parler</strong> — rejouer une consultation fictive écrite
          pour les tests
        </summary>
        <p className="muted" style={{ marginTop: 12 }}>
          Oris la traite comme une vraie : transcription, faits, documents. Utile pour voir
          le résultat sans micro.
        </p>
        {[...grouped.entries()].map(([domain, items]) => (
          <div key={domain} style={{ marginTop: 16 }}>
            <h3>{DOMAIN[domain] ?? domain}</h3>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {items.slice(0, 6).map((item) => (
                <button
                  key={item.case_id}
                  type="button"
                  className="button button-secondary"
                  disabled={busy}
                  onClick={() => void runSynthetic(item.case_id)}
                >
                  {item.patient_first_name} {item.patient_last_name}
                </button>
              ))}
            </div>
          </div>
        ))}
      </details>
    </div>
  );
}
